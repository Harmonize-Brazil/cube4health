<?xml version='1.0' encoding='utf-8'?>
<ns0:StyledLayerDescriptor xmlns:ns0="http://www.opengis.net/sld" xmlns:ns2="http://www.opengis.net/ogc" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.0.0" xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd">
  <ns0:NamedLayer>
    <ns0:Name>Relative Humidity</ns0:Name>
    <ns0:UserStyle>
      <ns0:Title>Relative Humidity Style</ns0:Title>
      <ns0:FeatureTypeStyle>
        <!-- Rule 1:  0 per -->
        <ns0:Rule>
          <ns0:Name>Rule 1</ns0:Name>
          <ns0:Title>0 %</ns0:Title>
          <ns2:Filter>
            <ns2:PropertyIsLessThanOrEqualTo>
              <ns2:PropertyName>value</ns2:PropertyName>
              <ns2:Literal>5</ns2:Literal>
            </ns2:PropertyIsLessThanOrEqualTo>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#FFFFFF</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#FFFFFF</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 2: 10 per -->
        <ns0:Rule>
          <ns0:Name>Rule 2</ns0:Name>
          <ns0:Title>10 %</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>5</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>15</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#DCDCDC</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#DCDCDC</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 3: 20 per -->
        <ns0:Rule>
          <ns0:Name>Rule 3</ns0:Name>
          <ns0:Title>20 %</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>15</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>25</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#FFB6B2</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#FFB6B2</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 4: 30 per -->
        <ns0:Rule>
          <ns0:Name>Rule 4</ns0:Name>
          <ns0:Title>30 %</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>25</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>35</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#FF8942</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#FF8942</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 5: 40 per -->
        <ns0:Rule>
          <ns0:Name>Rule 5</ns0:Name>
          <ns0:Title>40 %</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>35</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>45</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#F5DB82</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#F5DB82</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 6: 50 per -->
        <ns0:Rule>
          <ns0:Name>Rule 6</ns0:Name>
          <ns0:Title>50 %</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>45</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>55</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#DBE296</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#DBE296</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 7: 60 per -->
        <ns0:Rule>
          <ns0:Name>Rule 7</ns0:Name>
          <ns0:Title>60 %</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>55</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>65</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#BED3A1</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#BED3A1</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 8: 70 per -->
        <ns0:Rule>
          <ns0:Name>Rule 8</ns0:Name>
          <ns0:Title>70 %</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>65</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>75</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#9ECDBA</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#9ECDBA</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
		    <!-- Rule 7: 80 per -->
        <ns0:Rule>
          <ns0:Name>Rule 9</ns0:Name>
          <ns0:Title>80 %</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>75</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>85</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#8CB6DA</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#8CB6DA</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 8: 90 per -->
		<ns0:Rule>
          <ns0:Name>Rule 10</ns0:Name>
          <ns0:Title>90 %</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>85</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>95</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#4E8DD0</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#4E8DD0</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 8: 100 per -->
		<ns0:Rule>
          <ns0:Name>Rule 11</ns0:Name>
          <ns0:Title>100 %</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>95</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#2C5AA8</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#2C5AA8</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 8: 100 mm -->
      </ns0:FeatureTypeStyle>
    </ns0:UserStyle>
  </ns0:NamedLayer>
</ns0:StyledLayerDescriptor>
