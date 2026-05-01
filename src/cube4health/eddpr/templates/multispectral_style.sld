<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor version="1.0.0"
    xmlns:sld="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="
      http://www.opengis.net/sld
      http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">

  <sld:NamedLayer>
    <sld:Name>multispectral-imagemosaic</sld:Name>

    <sld:UserStyle>
      <sld:Title>False Color Stable (No Zoom Variance)</sld:Title>
      <sld:Abstract>
        Production-safe SLD 1.0 for ImageMosaic + COG.
        Fixed stretch, no dynamic normalization.
        Identical colors across zoom levels and tiles.
      </sld:Abstract>

      <sld:FeatureTypeStyle>
        <sld:Rule>

          <sld:RasterSymbolizer>

            <!-- Opacity -->
            <sld:Opacity>1.0</sld:Opacity>

            <!-- RGB channel mapping -->
            <sld:ChannelSelection>

              <!-- Red -->
              <sld:RedChannel>
                <sld:SourceChannelName>1</sld:SourceChannelName>
                <sld:ContrastEnhancement>
                  <sld:Normalize>
                    <sld:VendorOption name="minValue">500</sld:VendorOption>
                    <sld:VendorOption name="maxValue">45000</sld:VendorOption>
                  </sld:Normalize>
                </sld:ContrastEnhancement>
              </sld:RedChannel>

              <!-- NIR → Green (vegetation green) -->
              <sld:GreenChannel>
                <sld:SourceChannelName>3</sld:SourceChannelName>
                <sld:ContrastEnhancement>
                  <sld:Normalize>
                    <sld:VendorOption name="minValue">500</sld:VendorOption>
                    <sld:VendorOption name="maxValue">50000</sld:VendorOption>
                  </sld:Normalize>
                </sld:ContrastEnhancement>
              </sld:GreenChannel>

              <!-- Green -->
              <sld:BlueChannel>
                <sld:SourceChannelName>2</sld:SourceChannelName>
                <sld:ContrastEnhancement>
                  <sld:Normalize>
                    <sld:VendorOption name="minValue">500</sld:VendorOption>
                    <sld:VendorOption name="maxValue">45000</sld:VendorOption>
                  </sld:Normalize>
                </sld:ContrastEnhancement>
              </sld:BlueChannel>

            </sld:ChannelSelection>

            <!-- ImageMosaic overlap -->
            <sld:OverlapBehavior>
              <sld:AVERAGE/>
            </sld:OverlapBehavior>

          </sld:RasterSymbolizer>

        </sld:Rule>
      </sld:FeatureTypeStyle>

    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>