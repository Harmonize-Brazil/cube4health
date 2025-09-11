<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor version="1.0.0"
    xmlns:sld="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:gml="http://www.opengis.net/gml"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  <sld:NamedLayer>
    <sld:Name>Default Styler</sld:Name>
    <sld:UserStyle>
      <sld:Name>Default Styler</sld:Name>
      <sld:FeatureTypeStyle>
                <sld:Rule>
                    <sld:RasterSymbolizer>
                        <sld:Opacity>1.0</sld:Opacity>
                      <sld:ColorMap>
                        <sld:ColorMapEntry color="#ffffff" opacity="0" quantity="0" label="nodata"/>
                        <sld:ColorMapEntry color="#0092ED" quantity="2" label="2 C°"/>
                        <sld:ColorMapEntry color="#54BDFF" quantity="4" label="4 C°"/>
                        <sld:ColorMapEntry color="#05F4FF" quantity="8" label="8 C°"/>
                        <sld:ColorMapEntry color="#59FFCF" quantity="12" label="12 C°"/>
                        <sld:ColorMapEntry color="#51FF88" quantity="16" label="16 C°"/>
                        <sld:ColorMapEntry color="#4AFF00" quantity="20" label="20 C°"/>
                        <sld:ColorMapEntry color="#BCFF00" quantity="24" label="24 C°"/>
                        <sld:ColorMapEntry color="#F6E300" quantity="28" label="28 C°"/>
                        <sld:ColorMapEntry color="#F4C400" quantity="30" label="30 C°"/>
                        <sld:ColorMapEntry color="#F3A600" quantity="32" label="32 C°"/>
                        <sld:ColorMapEntry color="#F27D00" quantity="34" label="34 C°"/>
                        <sld:ColorMapEntry color="#F14900" quantity="36" label="36 C°"/>
                        <sld:ColorMapEntry color="#F02200" quantity="38" label="38 C°"/>
                        <sld:ColorMapEntry color="#F01300" quantity="40" label="40 C°"/>
                        <sld:ColorMapEntry color="#7E7E7E" quantity="60" label="60 C°"/>
                      </sld:ColorMap>
                    </sld:RasterSymbolizer>
                </sld:Rule>
            </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>