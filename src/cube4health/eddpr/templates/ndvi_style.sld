<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor version="1.0.0"
    xmlns:sld="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="
      http://www.opengis.net/sld
      http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">

  <sld:NamedLayer>
    <sld:Name>ndvi-style</sld:Name>

    <sld:UserStyle>
      <sld:Title>NDVI Stable Style</sld:Title>
      <sld:Abstract>
        NDVI style from -1 to 1 using fixed intervals.
        Stable across zoom levels and mosaic tiles.
      </sld:Abstract>

      <sld:FeatureTypeStyle>
        <sld:Rule>

          <sld:RasterSymbolizer>
            <sld:Opacity>1.0</sld:Opacity>

            <sld:ColorMap type="intervals">

              <!-- NoData -->
              <sld:ColorMapEntry
                quantity="-9999"
                color="#FFFFFF"
                opacity="0.0"
                label="NoData"/>

              <!-- NDVI scale -->
              <sld:ColorMapEntry quantity="-1.0"   color="#A52A2A" label="-1.00"/>
              <sld:ColorMapEntry quantity="-0.302" color="#E3BE0C" label="-0.30"/>
              <sld:ColorMapEntry quantity="-0.176" color="#EFD907" label="-0.18"/>
              <sld:ColorMapEntry quantity="-0.004" color="#FEFE00" label="-0.00"/>
              <sld:ColorMapEntry quantity="0.027"  color="#F8FB00" label="0.03"/>
              <sld:ColorMapEntry quantity="0.075"  color="#ECF500" label="0.08"/>
              <sld:ColorMapEntry quantity="0.122"  color="#E0EF00" label="0.12"/>
              <sld:ColorMapEntry quantity="0.153"  color="#D8EB00" label="0.15"/>
              <sld:ColorMapEntry quantity="0.176"  color="#D2E800" label="0.18"/>
              <sld:ColorMapEntry quantity="0.231"  color="#C3E100" label="0.23"/>
              <sld:ColorMapEntry quantity="0.263"  color="#BCDD00" label="0.26"/>
              <sld:ColorMapEntry quantity="0.333"  color="#AAD400" label="0.33"/>
              <sld:ColorMapEntry quantity="0.365"  color="#A2D000" label="0.37"/>
              <sld:ColorMapEntry quantity="0.435"  color="#90C700" label="0.44"/>
              <sld:ColorMapEntry quantity="0.467"  color="#88C300" label="0.47"/>
              <sld:ColorMapEntry quantity="0.553"  color="#71B800" label="0.55"/>
              <sld:ColorMapEntry quantity="0.647"  color="#59AC00" label="0.65"/>
              <sld:ColorMapEntry quantity="0.749"  color="#409F00" label="0.75"/>
              <sld:ColorMapEntry quantity="0.851"  color="#269200" label="0.85"/>
              <sld:ColorMapEntry quantity="0.953"  color="#0C8500" label="0.95"/>
              <sld:ColorMapEntry quantity="1.0"    color="#008000" label="1.00"/>

            </sld:ColorMap>

          </sld:RasterSymbolizer>

        </sld:Rule>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>