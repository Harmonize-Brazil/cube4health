<?xml version='1.0' encoding='utf-8'?>
<ns0:StyledLayerDescriptor xmlns:ns0="http://www.opengis.net/sld" xmlns:ns2="http://www.opengis.net/ogc" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.0.0" xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd">
  <ns0:NamedLayer>
    <ns0:Name>Precipitation</ns0:Name>
    <ns0:UserStyle>
      <ns0:Title>Precipitation Style</ns0:Title>
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
        <!-- Rule 1:  0.0000 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 2</ns0:Name>
          <ns0:Title>0.0000 mm</ns0:Title>
          <ns2:Filter>
            <ns2:PropertyIsLessThanOrEqualTo>
              <ns2:PropertyName>value</ns2:PropertyName>
              <ns2:Literal>0.00005</ns2:Literal>
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
        <!-- Rule 2: 0.0001 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 3</ns0:Name>
          <ns0:Title>0.0001 mm</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>0.00005</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>0.05005</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#F39000</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#F39000</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 3: 0.1 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 4</ns0:Name>
          <ns0:Title>0.1 mm</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>0.05005</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>0.55005</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#F5B803</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#F5B803</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 4: 1 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 5</ns0:Name>
          <ns0:Title>1 mm</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>0.55005</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>1.5</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#F7E000</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#F7E000</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 5: 2 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 6</ns0:Name>
          <ns0:Title>2 mm</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>1.5</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>2.5</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#F4FD00</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#F4FD00</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 6: 3 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 7</ns0:Name>
          <ns0:Title>3 mm</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>2.5</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>3.5</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#D2FE03</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#D2FE03</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 7: 4 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 8</ns0:Name>
          <ns0:Title>4 mm</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>3.5</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>4.5</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#9EFB01</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#9EFB01</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 8: 5 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 9</ns0:Name>
          <ns0:Title>5 mm</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>4.5</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>7.5</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#5AFE96</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#5AFE96</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 9: 10 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 10</ns0:Name>
          <ns0:Title>10 mm</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>7.5</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>15</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#51FE96</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#51FE96</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 10: 20 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 11</ns0:Name>
          <ns0:Title>20 mm</ns0:Title>
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
              <ns0:CssParameter name="fill">#56FDBD</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#56FDBD</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 11: 30 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 12</ns0:Name>
          <ns0:Title>30 mm</ns0:Title>
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
              <ns0:CssParameter name="fill">#5DFEE6</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#5DFEE6</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 12: 40 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 13</ns0:Name>
          <ns0:Title>40 mm</ns0:Title>
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
              <ns0:CssParameter name="fill">#5DEFFE</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#5DEFFE</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 13: 50 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 14</ns0:Name>
          <ns0:Title>50 mm</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>45</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>75</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#53C3F8</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#53C3F8</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 14: 100 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 15</ns0:Name>
          <ns0:Title>100 mm</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>75</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>150</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#4E9FFE</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#4E9FFE</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 15: 200 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 16</ns0:Name>
          <ns0:Title>200 mm</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>150</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>250</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#4675FA</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#4675FA</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 16: 300 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 17</ns0:Name>
          <ns0:Title>300 mm</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>250</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>350</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#444FFE</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#444FFE</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 17: 400 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 18</ns0:Name>
          <ns0:Title>400 mm</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>350</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>450</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#4128FE</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#4128FE</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 18: 500 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 19</ns0:Name>
          <ns0:Title>500 mm</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>450</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>600</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#3C07F0</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#3C07F0</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 19: 700 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 17</ns0:Name>
          <ns0:Title>700 mm</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>600</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
              <ns2:PropertyIsLessThanOrEqualTo>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>850</ns2:Literal>
              </ns2:PropertyIsLessThanOrEqualTo>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#9A74F4</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#9A74F4</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
        <!-- Rule 20: 1000 mm -->
        <ns0:Rule>
          <ns0:Name>Rule 21</ns0:Name>
          <ns0:Title>1000 mm</ns0:Title>
          <ns2:Filter>
            <ns2:And>
              <ns2:PropertyIsGreaterThan>
                <ns2:PropertyName>value</ns2:PropertyName>
                <ns2:Literal>850</ns2:Literal>
              </ns2:PropertyIsGreaterThan>
            </ns2:And>
          </ns2:Filter>
          <ns0:PolygonSymbolizer>
            <ns0:Fill>
              <ns0:CssParameter name="fill">#7659B7</ns0:CssParameter>
              <ns0:CssParameter name="fill-opacity">0.7</ns0:CssParameter>
            </ns0:Fill>
            <ns0:Stroke>
              <ns0:CssParameter name="stroke">#7659B7</ns0:CssParameter>
            </ns0:Stroke>
          </ns0:PolygonSymbolizer>
        </ns0:Rule>
      </ns0:FeatureTypeStyle>
    </ns0:UserStyle>
  </ns0:NamedLayer>
</ns0:StyledLayerDescriptor>

