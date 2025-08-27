<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:sld="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:gml="http://www.opengis.net/gml" version="1.0.0">
  <sld:UserLayer>
    <sld:LayerFeatureConstraints>
      <sld:FeatureTypeConstraint/>
    </sld:LayerFeatureConstraints>
    <sld:UserStyle>
      <sld:Title/>
      <sld:FeatureTypeStyle>
        <sld:Name>Precipitation</sld:Name>
        <sld:FeatureTypeName>Feature</sld:FeatureTypeName>
        <sld:Rule>
          <sld:MinScaleDenominator>75000</sld:MinScaleDenominator>
          <sld:RasterSymbolizer>
            <sld:Geometry>
              <ogc:PropertyName>grid</ogc:PropertyName>
            </sld:Geometry>
            <sld:ColorMap>
	      <sld:ColorMapEntry color="#ffffff" quantity="0" label="nodata" opacity="0"/>
              <sld:ColorMapEntry color="#F39000" quantity="5" label="5 mm"/>
              <sld:ColorMapEntry color="#F5B803" quantity="10" label="10 mm"/>
              <sld:ColorMapEntry color="#F7E000" quantity="20" label="20 mm"/>
              <sld:ColorMapEntry color="#F4FD00" quantity="30" label="30 mm"/>
              <sld:ColorMapEntry color="#D2FE03" quantity="40" label="40 mm"/>
              <sld:ColorMapEntry color="#9EFB01" quantity="50" label="50 mm"/>
              <sld:ColorMapEntry color="#5AFE96" quantity="100" label="100 mm"/>
              <sld:ColorMapEntry color="#51FE96" quantity="150" label="150 mm"/>
              <sld:ColorMapEntry color="#56FDBD" quantity="200" label="200 mm"/>
              <sld:ColorMapEntry color="#5DFEE6" quantity="250" label="250 mm"/>
              <sld:ColorMapEntry color="#5DEFFE" quantity="300" label="300 mm"/>
              <sld:ColorMapEntry color="#53C3F8" quantity="350" label="350 mm"/>
              <sld:ColorMapEntry color="#4E9FFE" quantity="400" label="400 mm"/>
              <sld:ColorMapEntry color="#4675FA" quantity="500" label="500 mm"/>
              <sld:ColorMapEntry color="#444FFE" quantity="600" label="600 mm"/>
              <sld:ColorMapEntry color="#4128FE" quantity="700" label="700 mm"/>
              <sld:ColorMapEntry color="#3C07F0" quantity="800" label="800 mm"/>
              <sld:ColorMapEntry color="#9A74F4" quantity="900" label="900 mm"/>
              <sld:ColorMapEntry color="#7659B7" quantity="1000" label="1000 mm"/>
            </sld:ColorMap>
          </sld:RasterSymbolizer>
        </sld:Rule>
        <sld:VendorOption name="composite">multiply</sld:VendorOption>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:UserLayer>
</sld:StyledLayerDescriptor>