<?xml version='1.0' encoding='utf-8'?>
<ns0:StyledLayerDescriptor xmlns:ns0="http://www.opengis.net/sld" xmlns:ns2="http://www.opengis.net/ogc" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.0.0" xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd">
  <ns0:NamedLayer>
    <ns0:Name>Anomaly</ns0:Name>
    <ns0:UserStyle>
      <ns0:Title>Anomaly Style</ns0:Title>
      <ns0:FeatureTypeStyle>
        <!-- Rule 1:  0 days -->
        <ns0:Rule>
          <ns0:Name>Rule 1</ns0:Name>
          <ns0:Title>0 days</ns0:Title>
          <ns2:Filter>
            <ns2:PropertyIsEqualTo>
              <ns2:PropertyName>value</ns2:PropertyName>
              <ns2:Literal>0</ns2:Literal>
            </ns2:PropertyIsEqualTo>
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
        <!-- Rule 2: 1 day -->
        <ns0:Rule>
          <ns0:Name>Rule 2</ns0:Name>
          <ns0:Title>1 day</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>1</ns2:Literal>
              </ns2:PropertyIsEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#FFFFCC</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#FFFFCC</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 3: 2 days -->
        <ns0:Rule>
          <ns0:Name>Rule 3</ns0:Name>
          <ns0:Title>2 days</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>2</ns2:Literal>
              </ns2:PropertyIsEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#C7E9B4</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#C7E9B4</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 4: 3 days -->
        <ns0:Rule>
          <ns0:Name>Rule 4</ns0:Name>
          <ns0:Title>3 days</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>3</ns2:Literal>
              </ns2:PropertyIsEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#7FCDBB</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#7FCDBB</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 5: 4 days -->
        <ns0:Rule>
          <ns0:Name>Rule 5</ns0:Name>
          <ns0:Title>4 days</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>4</ns2:Literal>
              </ns2:PropertyIsEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#41B6C4</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#41B6C4</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 6: 5 days -->
        <ns0:Rule>
          <ns0:Name>Rule 6</ns0:Name>
          <ns0:Title>5 days</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>5</ns2:Literal>
              </ns2:PropertyIsEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#1D91C0</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#1D91C0</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 7: 6 days -->
        <ns0:Rule>
          <ns0:Name>Rule 7</ns0:Name>
          <ns0:Title>6 days</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>6</ns2:Literal>
              </ns2:PropertyIsEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#225EA8</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#225EA8</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 8: 7 days -->
        <ns0:Rule>
          <ns0:Name>Rule 8</ns0:Name>
          <ns0:Title>7 days</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>7</ns2:Literal>
              </ns2:PropertyIsEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#0C2C84</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#0C2C84</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
      </ns0:FeatureTypeStyle>
    </ns0:UserStyle>
  </ns0:NamedLayer>
</ns0:StyledLayerDescriptor>
