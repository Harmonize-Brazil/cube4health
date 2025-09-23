<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:sld="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:gml="http://www.opengis.net/gml" version="1.0.0">
  <sld:UserLayer>
    <sld:LayerFeatureConstraints>
      <sld:FeatureTypeConstraint/>
    </sld:LayerFeatureConstraints>
    <sld:UserStyle>
      <sld:Title/>
      <sld:FeatureTypeStyle>
        <sld:Name>Relative Humidity</sld:Name>
        <sld:FeatureTypeName>Feature</sld:FeatureTypeName>
        <sld:Rule>
          <sld:MinScaleDenominator>75000</sld:MinScaleDenominator>
          <sld:RasterSymbolizer>
            <sld:Geometry>
              <ogc:PropertyName>grid</ogc:PropertyName>
            </sld:Geometry>
            <sld:ColorMap>
              <sld:ColorMapEntry color="#FFFFFF" opacity="0.85" quantity="0" label="0 %"/>
              <sld:ColorMapEntry color="#DCDCDC" opacity="0.85" quantity="10" label="10 %"/>
              <sld:ColorMapEntry color="#FFB6B2" opacity="0.85" quantity="20" label="20 %"/>
              <sld:ColorMapEntry color="#FF8942" opacity="0.85" quantity="30" label="30 %"/>
              <sld:ColorMapEntry color="#F5DB82" opacity="0.85" quantity="40" label="40 %"/>
              <sld:ColorMapEntry color="#DBE296" opacity="0.85" quantity="50" label="50 %"/>
              <sld:ColorMapEntry color="#BED3A1" opacity="0.85" quantity="60" label="60 %"/>
              <sld:ColorMapEntry color="#9ECDBA" opacity="0.85" quantity="70" label="70 %"/>
              <sld:ColorMapEntry color="#8CB6DA" opacity="0.85" quantity="80" label="80 %"/>
              <sld:ColorMapEntry color="#4E8DD0" opacity="0.85" quantity="90" label="90 %"/>
              <sld:ColorMapEntry color="#2C5AA8" opacity="0.85" quantity="100" label="100 %"/>
            </sld:ColorMap>
          </sld:RasterSymbolizer>
        </sld:Rule>
        <sld:VendorOption name="composite">multiply</sld:VendorOption>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:UserLayer>
</sld:StyledLayerDescriptor>
