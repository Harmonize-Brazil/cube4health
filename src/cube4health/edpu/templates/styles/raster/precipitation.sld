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
          <sld:MinScaleDenominator>0</sld:MinScaleDenominator>
          <sld:RasterSymbolizer>
            <sld:Geometry>
              <ogc:PropertyName>grid</ogc:PropertyName>
            </sld:Geometry>
            <sld:ColorMap>
              <sld:ColorMapEntry color="#ffffff" opacity="0" quantity="-9999" label="nodata" />
            	<sld:ColorMapEntry color="#FFFFFF" opacity="0.85" quantity="0.0000" label="0.0000 mm"/>
              <sld:ColorMapEntry color="#F39000" opacity="0.85" quantity="0.0001" label="0.0001 mm"/>
              <sld:ColorMapEntry color="#F5B803" opacity="0.85" quantity="0.1" label="0.1 mm"/>
              <sld:ColorMapEntry color="#F7E000" opacity="0.85" quantity="1" label="1 mm"/>
              <sld:ColorMapEntry color="#F4FD00" opacity="0.85" quantity="2" label="2 mm"/>
              <sld:ColorMapEntry color="#D2FE03" opacity="0.85" quantity="3" label="3 mm"/>
              <sld:ColorMapEntry color="#9EFB01" opacity="0.85" quantity="4" label="4 mm"/>
              <sld:ColorMapEntry color="#5AFE96" opacity="0.85" quantity="5" label="5 mm"/>
              <sld:ColorMapEntry color="#51FE96" opacity="0.85" quantity="10" label="10 mm"/>
              <sld:ColorMapEntry color="#56FDBD" opacity="0.85" quantity="20" label="20 mm"/>
              <sld:ColorMapEntry color="#5DFEE6" opacity="0.85" quantity="30" label="30 mm"/>
              <sld:ColorMapEntry color="#5DEFFE" opacity="0.85" quantity="40" label="40 mm"/>
              <sld:ColorMapEntry color="#53C3F8" opacity="0.85" quantity="50" label="50 mm"/>
              <sld:ColorMapEntry color="#4E9FFE" opacity="0.85" quantity="100" label="100 mm"/>
              <sld:ColorMapEntry color="#4675FA" opacity="0.85" quantity="200" label="200 mm"/>
              <sld:ColorMapEntry color="#444FFE" opacity="0.85" quantity="300" label="300 mm"/>
              <sld:ColorMapEntry color="#4128FE" opacity="0.85" quantity="400" label="400 mm"/>
              <sld:ColorMapEntry color="#3C07F0" opacity="0.85" quantity="500" label="500 mm"/>
              <sld:ColorMapEntry color="#9A74F4" opacity="0.85" quantity="700" label="700 mm"/>
              <sld:ColorMapEntry color="#7659B7" opacity="0.85" quantity="1000" label="1000 mm"/>
            </sld:ColorMap>
          </sld:RasterSymbolizer>
        </sld:Rule>
        <sld:VendorOption name="composite">multiply</sld:VendorOption>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:UserLayer>
</sld:StyledLayerDescriptor>
