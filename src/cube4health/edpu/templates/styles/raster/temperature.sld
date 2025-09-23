<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:sld="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:gml="http://www.opengis.net/gml" version="1.0.0">
  <sld:UserLayer>
    <sld:LayerFeatureConstraints>
      <sld:FeatureTypeConstraint/>
    </sld:LayerFeatureConstraints>
    <sld:UserStyle>
      <sld:Title/>
      <sld:FeatureTypeStyle>
        <sld:Name>Temperature</sld:Name>
        <sld:FeatureTypeName>Feature</sld:FeatureTypeName>
        <sld:Rule>
          <sld:MinScaleDenominator>75000</sld:MinScaleDenominator>
          <sld:RasterSymbolizer>
            <sld:Geometry>
              <ogc:PropertyName>grid</ogc:PropertyName>
            </sld:Geometry>
            <sld:ColorMap>
	      <sld:ColorMapEntry color="#ffffff" quantity="-999000000" label="nodata" opacity="0"/>
              <sld:ColorMapEntry color="#003696" opacity="0.85" quantity="-20" label="-20 C°"/>
              <sld:ColorMapEntry color="#0092ED" opacity="0.85" quantity="0" label="0 C°"/>
              <sld:ColorMapEntry color="#54BDFF" opacity="0.85" quantity="4" label="4 C°"/>
              <sld:ColorMapEntry color="#05F4FF" opacity="0.85" quantity="8" label="8 C°"/>
              <sld:ColorMapEntry color="#59FFCF" opacity="0.85" quantity="12" label="12 C°"/>
              <sld:ColorMapEntry color="#51FF88" opacity="0.85" quantity="16" label="16 C°"/>
              <sld:ColorMapEntry color="#4AFF00" opacity="0.85" quantity="20" label="20 C°"/>
              <sld:ColorMapEntry color="#BCFF00" opacity="0.85" quantity="24" label="24 C°"/>
              <sld:ColorMapEntry color="#F6E300" opacity="0.85" quantity="28" label="28 C°"/>
              <sld:ColorMapEntry color="#F4C400" opacity="0.85" quantity="30" label="30 C°"/>
              <sld:ColorMapEntry color="#F3A600" opacity="0.85" quantity="32" label="32 C°"/>
              <sld:ColorMapEntry color="#F27D00" opacity="0.85" quantity="34" label="34 C°"/>
              <sld:ColorMapEntry color="#F14900" opacity="0.85" quantity="36" label="36 C°"/>
              <sld:ColorMapEntry color="#F02200" opacity="0.85" quantity="38" label="38 C°"/>
              <sld:ColorMapEntry color="#F01300" opacity="0.85" quantity="40" label="40 C°"/>
              <sld:ColorMapEntry color="#7E7E7E" opacity="0.85" quantity="60" label="60 C°"/>
            </sld:ColorMap>
          </sld:RasterSymbolizer>
        </sld:Rule>
        <sld:VendorOption name="composite">multiply</sld:VendorOption>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:UserLayer>
</sld:StyledLayerDescriptor>
