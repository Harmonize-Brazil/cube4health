# inbuilt libraries
import os
import re
import time
import threading
import logging
from collections import deque
from typing import Optional, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

# third-party libraries
import psutil
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
import geopandas as gpd
from tqdm import tqdm

# custom libraries
from cube4health.ehipr.utils import check_date_format
from cube4health.ehipr.ehipr import _check_existence_dirs, _get_indicator_info  # TODO: remover importacao check_exist

from cube4health.ehipr.config import CPU_COUNT

logger = logging.getLogger(__name__)

# URL of the API
ROUTE = "https://api.mosqlimate.org/api/datastore/infodengue/"

# IDs of the disease
DISEASE_IDS = {
    'dengue': 'dengue',
    'chikungunya': 'chik',
    'zika': 'zika'
}

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
# The API allows at most 10 requests/second. We keep a safety margin below
# that (default 8/s) because the limiter only controls when *we* send a
# request — network jitter/queueing can still cause us to graze the limit.
MAX_REQUESTS_PER_SECOND = 8


class RateLimiter:
    """
    Thread-safe sliding-window rate limiter.

    Guarantees that no more than `max_calls` calls to `acquire()` return
    within any rolling `period` window, across ALL threads sharing the
    same instance. This is what actually stops you from bursting past the
    API's 10 req/s cap when you have multiple worker threads firing at once.
    """

    def __init__(self, max_calls: int, period: float = 1.0):
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()
        self.lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            sleep_time = 0.0
            with self.lock:
                now = time.monotonic()
                # drop timestamps that fell out of the window
                while self.calls and now - self.calls[0] > self.period:
                    self.calls.popleft()

                if len(self.calls) < self.max_calls:
                    self.calls.append(now)
                    return

                # window is full: figure out how long until the oldest
                # call expires, and retry after that
                sleep_time = self.period - (now - self.calls[0])

            # sleep OUTSIDE the lock so other threads aren't blocked
            time.sleep(max(sleep_time, 0.01))


_rate_limiter = RateLimiter(max_calls=MAX_REQUESTS_PER_SECOND, period=1.0)


def _build_session() -> requests.Session:
    """
    Builds a requests.Session with automatic retry/backoff for 429 and
    transient 5xx errors. This handles the REACTIVE side (what to do when
    the API says "too many requests"), while `_rate_limiter` handles the
    PROACTIVE side (not sending too many requests in the first place).

    `respect_retry_after_header=True` makes urllib3 honor a `Retry-After`
    header if the API sends one on a 429 response; otherwise it falls back
    to exponential backoff (1s, 2s, 4s, 8s, 16s with backoff_factor=1).
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
        raise_on_status=True,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_maxsize=CPU_COUNT + 5)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def __batch_generator(data, batch_size):
    batch = []
    for item in data:
        batch.append(item)
        if len(batch) == batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def __check_memory_limit(max_memory_usage: int) -> bool:
    """
    Check if the memory usage is above the limit.
    """
    memory_info = psutil.virtual_memory()
    if memory_info.percent >= max_memory_usage:
        return True
    return False


def compose_url(disease: str,
                start_date: str,
                end_date: str,
                page: Optional[int]=1,
                code: Optional[Union[str, int]]=None) -> str:
    """
    Composes the URL to fetch data from the API
    """
    pagination = f"?page={page}&per_page=100&"

    # NOTE: previously this function overwrote disease/start_date/end_date
    # with hardcoded debug values here, ignoring whatever was passed in.
    # That's removed — the function now genuinely uses its parameters.

    # Making the filter request according to the code information (geocode or uf)
    if isinstance(code, int) or (isinstance(code, str) and len(code) > 2):
        filters = f"disease={disease}&start={start_date}&end={end_date}&geocode={code}"
    elif isinstance(code, str) and len(code) == 2:
        filters = f"disease={disease}&start={start_date}&end={end_date}&uf={code.upper()}"
    else:
        filters = f"disease={disease}&start={start_date}&end={end_date}"

    return ROUTE + pagination + filters


def fetch_data(session: requests.Session, url: str, headers: dict) -> dict:
    """
    Performs the actual HTTP GET, gated by the global rate limiter.
    """
    _rate_limiter.acquire()
    response = session.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def attempt_delay(session: requests.Session,
                  url: str,
                  headers: dict,
                  max_attempts: int = 8) -> dict:
    """
    Wraps fetch_data with bounded retries.

    Note: fetch_data's Session already retries 429/5xx internally via the
    urllib3 Retry adapter built in `_build_session`. This outer loop is a
    second safety net for other transient errors (e.g. connection resets)
    and, critically, is bounded — unlike the original implementation this
    replaces, it will NOT recurse forever and blow the stack on a
    persistent failure.
    """
    last_exception = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fetch_data(session=session, url=url, headers=headers)
        except requests.exceptions.HTTPError as e:
            last_exception = e
            status = e.response.status_code if e.response is not None else None
            wait = min(2 ** attempt, 30)
            logger.warning(
                "Request failed (status=%s, attempt=%d/%d) for %s. Retrying in %.1fs",
                status, attempt, max_attempts, url, wait
            )
            time.sleep(wait)
        except requests.exceptions.RequestException as e:
            last_exception = e
            wait = min(2 ** attempt, 30)
            logger.warning(
                "Connection error (attempt %d/%d) for %s: %s. Retrying in %.1fs",
                attempt, max_attempts, url, e, wait
            )
            time.sleep(wait)

    raise RuntimeError(
        f"Failed to fetch {url} after {max_attempts} attempts"
    ) from last_exception


def __save_to_csv(data: pd.DataFrame,
                  filename: str,
                  mode: Optional[str]=None,
                  overwrite: Optional[bool]=False) -> bool:
    """
    Save data to a CSV file.
    """
    _check_existence_dirs([os.path.dirname(filename)])

    if overwrite:
        if os.path.exists(filename):
            os.remove(filename)
        mode = 'w'

    if not mode:
        mode = 'a' if os.path.exists(filename) else 'w'

    try:
        data.to_csv(filename, mode=mode, index=False)
        return True
    except Exception:
        return False


def __request_data(disease: str,
                   start_date: str,
                   end_date: str,
                   token: str,
                   geocode: Optional[Union[str, int]]=[None]) -> Union[list, str]: # type: ignore
    """
    Fetch infoDengue indicator data from the API.
    """
    if not all(isinstance(arg, str) for arg in [disease, start_date, end_date]):
        return "Error: The parameters must be a string."

    if not check_date_format(date=start_date) and not check_date_format(date=end_date):
        return "Error: The start_date and end_date is not in the correct format (YYYY-MM-DD)."

    if geocode and isinstance(geocode, dict):
        try:
            geocode = gpd.read_file(geocode['path'])[geocode['code']].tolist()
        except IOError:
            return "Error: The filepath provided for the geocode variable is not valid."

    result = []
    headers = {"X-UID-Key": token}
    # A single session (with its retry-enabled adapter) is reused for all
    # requests, sequential or parallel — requests.Session is thread-safe
    # for concurrent use across threads sharing one adapter.
    with _build_session() as session:
        for code in tqdm(geocode, desc="Processing geocode"):
            url = compose_url(
                disease=disease,
                start_date=start_date,
                end_date=end_date,
                code=code
            )
            data = attempt_delay(session, url, headers)
            try:
                total_pages = data["pagination"]["total_pages"]
                result.extend(data["items"])
                futures = {}
            except KeyError:
                return 'Error: The API does not return any data. Check the parameters.'

            # max_workers is capped low on purpose: the RateLimiter already
            # throttles total throughput to MAX_REQUESTS_PER_SECOND, so extra
            # workers beyond that just queue up waiting on `acquire()`.
            # Keeping this small avoids opening more connections than useful
            # and keeps behavior predictable.
            with ThreadPoolExecutor(max_workers=min(CPU_COUNT, MAX_REQUESTS_PER_SECOND)) as executor:
                for page in range(1, total_pages + 1):
                    url = compose_url(disease=disease,
                                start_date=start_date,
                                end_date=end_date,
                                code=code,
                                page=page)
                    futures[executor.submit(attempt_delay, session, url, headers)] = url
                for future in tqdm(as_completed(futures),
                                    total=len(futures),
                                    desc="Downloading data from Mosqlimate/Infodengue API..."):
                    _ = futures[future]
                    resp = future.result()
                    if result:
                        resp["items"].extend(result)
                        result = []
                    for i in resp['items']:
                        yield i


def get_infodengue_indicator(indicator: str,
                             start_date: str,
                             end_date: str,
                             mosqlimate_token: str,
                             output_path: Optional[str]=None,
                             geocode: Optional[Union[str, int]]=[None],
                             overwrite: Optional[bool]=False) -> Union[bool, str]:
    """
    Get infoDengue indicator data from the API.
    """

    def adjust_df() -> pd.DataFrame:
        df = pd.DataFrame(all_items)
        df['agg_time'] = 'week'
        df['agg'] = 'municipality' if all(spt_agg) else 'state'
        df['name'] = indicator
        pd.set_option('future.no_silent_downcasting', True)
        df.fillna(0, inplace=True)
        return df[['name', 'data_iniSE', 'agg', 'agg_time', 'municipio_geocodigo', field_name]]

    try:
        indicator_info = _get_indicator_info(provider='infodengue', id=indicator)

        if not indicator_info.get("status"):
            return indicator_info.get("message")

        indicator_info = indicator_info.get("indicator")

        field_name = indicator_info.get('field_name')

        disease = indicator_info.get('disease')
        disease_id = DISEASE_IDS[disease.lower()]
    except Exception:
        return "Error: The disease must be one of the "\
               "following: %s." % ', '.join(DISEASE_IDS.keys())

    try:
        if not isinstance(mosqlimate_token, str) or not mosqlimate_token:
            raise Exception("The 'token' is empty or is not a string.")

        try:
            _, token = mosqlimate_token.split(':')
            _ = re.match(r"^[a-f0-9\-]{36}[a-z]?$", token) is not None
        except ValueError:
            raise Exception("The 'token' is invalid.")

    except Exception as e:
        return f"Error: {str(e)}"

    try:
        data = __request_data(
            disease=disease_id,
            start_date=start_date,
            end_date=end_date,
            token=mosqlimate_token,
            geocode=geocode
        )

        if isinstance(data, str):
            raise Exception(data)

        spt_agg = [True if code is None or len(code) != 2 else False for code in geocode]
        all_items = []

    except Exception as e:
        return f"Error: {str(e)}"

    try:
        output_path = os.path.join(output_path, indicator)
        _check_existence_dirs([output_path])
        filepath = os.path.join(output_path, f'{indicator}.csv')

        if os.path.exists(filepath) and overwrite:
            os.remove(filepath)

        for item in tqdm(data, desc="Saving data to CSV file..."):
            all_items.append(item)
            if len(all_items) == 1000:
                df = adjust_df().drop_duplicates()
                __save_to_csv(data=df, filename=filepath)
                all_items = []

        if all_items:
            df = adjust_df().drop_duplicates()
            __save_to_csv(data=df, filename=filepath)
            all_items = []
            return output_path
        raise Exception("Cannot save the indicator!")
    except KeyError as e:
        return "Error: some parameter is not valid." if 'pagination' in str(e) else "Error: the "\
                "key 'data_iniSE' was not found in the data."
    except TypeError:
        return "Error: something went wrong when parsing the data to a Pandas DataFrame."
    except Exception as e:
        return f"Error: {str(e)}"