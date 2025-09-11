<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor version="1.0.0"
    xmlns:sld="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:gml="http://www.opengis.net/gml"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
    
    <sld:NamedLayer>
        <sld:Name>multispectral-style</sld:Name>
        <sld:UserStyle>
            <sld:Title>Multispectral Composition Raster Style</sld:Title>
            <sld:Abstract>Style for RGB composition of multispectral data from Mavic 3M.</sld:Abstract>
            <sld:FeatureTypeStyle>
            <!-- Info: https://docs.geoserver.org/maintain/en/user/styling/sld/reference/rastersymbolizer.html -->
                <sld:Rule>
                    <sld:RasterSymbolizer>
                        <sld:Opacity>1.0</sld:Opacity>
                        <ChannelSelection>
                          <RedChannel>
                            <SourceChannelName>1</SourceChannelName>
                            <!-- Info about Normalization: https://geoserver.geosolutionsgroup.com/edu/en/raster_data/advanced_gdal/example6.html -->
                            <ContrastEnhancement>
                            <Normalize>
                            <VendorOption name="algorithm">StretchToMinimumMaximum</VendorOption>
                            <VendorOption name="minValue">-0.0940898</VendorOption>
                            <VendorOption name="maxValue">0.2570492825</VendorOption>
                            </Normalize>
                           </ContrastEnhancement>
                          </RedChannel>
                          <GreenChannel>
                            <SourceChannelName>3</SourceChannelName>
                            <ContrastEnhancement>
                            <Normalize>
                            <VendorOption name="algorithm">StretchToMinimumMaximum</VendorOption>
                            <VendorOption name="minValue">-0.148967</VendorOption>
                            <VendorOption name="maxValue">0.401205</VendorOption>
                            </Normalize>
                           </ContrastEnhancement>
                          </GreenChannel>
                          <BlueChannel>
                            <SourceChannelName>2</SourceChannelName>
                             <ContrastEnhancement>
                            <Normalize>
                            <VendorOption name="algorithm">StretchToMinimumMaximum</VendorOption>
                            <VendorOption name="minValue">-0.0755059</VendorOption>
                            <VendorOption name="maxValue">0.188614</VendorOption>
                            </Normalize>
                           </ContrastEnhancement>
                          </BlueChannel>
                       </ChannelSelection>
                    </sld:RasterSymbolizer>
                </sld:Rule>
            </sld:FeatureTypeStyle>
        </sld:UserStyle>
    </sld:NamedLayer>
</sld:StyledLayerDescriptor>