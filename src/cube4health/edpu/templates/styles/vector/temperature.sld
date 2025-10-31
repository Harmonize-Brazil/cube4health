<?xml version='1.0' encoding='utf-8'?>
<ns0:StyledLayerDescriptor xmlns:ns0="http://www.opengis.net/sld" xmlns:ns2="http://www.opengis.net/ogc" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.0.0" xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd">
  <ns0:NamedLayer>
    <ns0:Name>Temperature</ns0:Name>
    <ns0:UserStyle>
      <ns0:Title>Temperature Style</ns0:Title>
      <ns0:FeatureTypeStyle>
        <!-- Rule 0:  nodata -->
        <ns0:Rule>
          <ns0:Name>Rule 1</ns0:Name>
          <ns0:Title>nodata</ns0:Title>
          <ns2:Filter>
            <ns2:PropertyIsEqualTo>
              <ns2:PropertyName>value</ns2:PropertyName>
              <ns2:Literal>-9999</ns2:Literal>
            </ns2:PropertyIsEqualTo>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#ffffff</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#ffffff</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 1: -20 C° -->
        <ns0:Rule>
          <ns0:Name>Rule 2</ns0:Name>
          <ns0:Title>-20 C°</ns0:Title>
          <ns2:Filter>
            <ns2:PropertyIsLessThanOrEqualTo>
              <ns2:PropertyName>value</ns2:PropertyName>
              <ns2:Literal>-20</ns2:Literal>
            </ns2:PropertyIsLessThanOrEqualTo>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#003696</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#003696</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 2: 0 C° -->
        <ns0:Rule>
          <ns0:Name>Rule 3</ns0:Name>
          <ns0:Title>0 C°</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>-20</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>2</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#0092ED</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#0092ED</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 3: 4 C° -->
        <ns0:Rule>
          <ns0:Name>Rule 4</ns0:Name>
          <ns0:Title>4 C°</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>2</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>6</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#54BDFF</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#54BDFF</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 4: 8 C° -->
        <ns0:Rule>
          <ns0:Name>Rule 5</ns0:Name>
          <ns0:Title>8 C°</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>6</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>10</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#05F4FF</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#05F4FF</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 5: 12 C° -->
        <ns0:Rule>
          <ns0:Name>Rule 6</ns0:Name>
          <ns0:Title>12 C°</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>10</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>14</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#59FFCF</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#59FFCF</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 6: 16 C° -->
        <ns0:Rule>
          <ns0:Name>Rule 7</ns0:Name>
          <ns0:Title>16 C°</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>14</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>18</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#51FF88</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#51FF88</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 7: 20 C° -->
        <ns0:Rule>
          <ns0:Name>Rule 8</ns0:Name>
          <ns0:Title>20 C°</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>18</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>22</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#4AFF00</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#4AFF00</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 8: 24 C° -->
        <ns0:Rule>
          <ns0:Name>Rule 9</ns0:Name>
          <ns0:Title>24 C°</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>22</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>25</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#BCFF00</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#BCFF00</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 9: 26 C° -->
        <ns0:Rule>
          <ns0:Name>Rule 10</ns0:Name>
          <ns0:Title>26 C°</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>25</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>27</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#F7FF00</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#F7FF00</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 10: 28 C° -->
        <ns0:Rule>
          <ns0:Name>Rule 11</ns0:Name>
          <ns0:Title>28 C°</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>27</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>29</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#F6E300</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#F6E300</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 11: 30 C° -->
        <ns0:Rule>
          <ns0:Name>Rule 12</ns0:Name>
          <ns0:Title>30 C°</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>29</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>31</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#F4C400</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#F4C400</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 12: 32 C° -->
        <ns0:Rule>
          <ns0:Name>Rule 13</ns0:Name>
          <ns0:Title>32 C°</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>31</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>33</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#F3A600</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#F3A600</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 13: 34 C° -->
        <ns0:Rule>
          <ns0:Name>Rule 14</ns0:Name>
          <ns0:Title>34 C°</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>33</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>35</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#F27D00</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#F27D00</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 14: 36 C° -->
        <ns0:Rule>
          <ns0:Name>Rule 15</ns0:Name>
          <ns0:Title>36 C°</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>35</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>37</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#F14900</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#F14900</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 15: 38 C° -->
        <ns0:Rule>
          <ns0:Name>Rule 16</ns0:Name>
          <ns0:Title>38 C°</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>37</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>39</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#F02200</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#F02200</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 16: 40 C° -->
        <ns0:Rule>
          <ns0:Name>Rule 17</ns0:Name>
          <ns0:Title>40 C°</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>39</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>50</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#F01300</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#F01300</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 17: 60 C° -->
        <ns0:Rule>
          <ns0:Name>Rule 18</ns0:Name>
          <ns0:Title>60 C°</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>50</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#7E7E7E</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#7E7E7E</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
      </ns0:FeatureTypeStyle>
    </ns0:UserStyle>
  </ns0:NamedLayer>
</ns0:StyledLayerDescriptor>
