<?xml version='1.0' encoding='utf-8'?>
<ns0:StyledLayerDescriptor xmlns:ns0="http://www.opengis.net/sld" xmlns:ns2="http://www.opengis.net/ogc" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.0.0" xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd">
  <ns0:NamedLayer>
    <ns0:Name>MyLayer</ns0:Name>
    <ns0:UserStyle>
      <ns0:Title>My Layer Style</ns0:Title>
      <ns0:FeatureTypeStyle>
        <ns0:Rule>
          <ns0:Name>Rule 1</ns0:Name>
          <ns0:Title>Lower than 167</ns0:Title>
          <ns2:Filter>
            <ns2:PropertyIsLessThan>
              <ns2:PropertyName>value</ns2:PropertyName>
              <ns2:Literal>167</ns2:Literal>
            </ns2:PropertyIsLessThan>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#d9d9d9</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#d9d9d9</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <ns0:Rule>
          <ns0:Name>Rule 2</ns0:Name>
          <ns0:Title>Between 167 and 167</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThanOrEqualTo>
                <ns2:PropertyName>propertie</ns2:PropertyName>
                <ns2:Literal>167</ns2:Literal>
              </ns2:PropertyIsGreaterThanOrEqualTo>
              <ns2:PropertyIsLessThan>
                <ns2:PropertyName>propertie</ns2:PropertyName>
                <ns2:Literal>167</ns2:Literal>
              </ns2:PropertyIsLessThan>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#f1b066</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#f1b066</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <ns0:Rule>
          <ns0:Name>Rule 3</ns0:Name>
          <ns0:Title>Between 167 and 167</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThanOrEqualTo>
                <ns2:PropertyName>propertie</ns2:PropertyName>
                <ns2:Literal>167</ns2:Literal>
              </ns2:PropertyIsGreaterThanOrEqualTo>
              <ns2:PropertyIsLessThan>
                <ns2:PropertyName>propertie</ns2:PropertyName>
                <ns2:Literal>167</ns2:Literal>
              </ns2:PropertyIsLessThan>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#e56d46</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#e56d46</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <ns0:Rule>
          <ns0:Name>Rule 4</ns0:Name>
          <ns0:Title>Between 167 and 167</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThanOrEqualTo>
                <ns2:PropertyName>propertie</ns2:PropertyName>
                <ns2:Literal>167</ns2:Literal>
              </ns2:PropertyIsGreaterThanOrEqualTo>
              <ns2:PropertyIsLessThan>
                <ns2:PropertyName>propertie</ns2:PropertyName>
                <ns2:Literal>167</ns2:Literal>
              </ns2:PropertyIsLessThan>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#c5444d</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#c5444d</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <ns0:Rule>
          <ns0:Name>Rule 5</ns0:Name>
          <ns0:Title>Greater than 167</ns0:Title>
          <ns2:Filter>
            <ns2:PropertyIsGreaterThanOrEqualTo>
              <ns2:PropertyName>vl_2010</ns2:PropertyName>
              <ns2:Literal>167</ns2:Literal>
            </ns2:PropertyIsGreaterThanOrEqualTo>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#922042</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#922042</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
      </ns0:FeatureTypeStyle>
    </ns0:UserStyle>
  </ns0:NamedLayer>
</ns0:StyledLayerDescriptor>
