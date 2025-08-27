<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor version="1.0.0"
    xmlns:sld="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:gml="http://www.opengis.net/gml"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
    
    <sld:NamedLayer>
        <sld:Name>ndvi-style</sld:Name>
        <sld:UserStyle>
            <sld:Title>NDVI Raster Style</sld:Title>
            <sld:Abstract>Style for NDVI values from -1 to 1, coloring from brown (low) to dark green (high).</sld:Abstract>
            <sld:FeatureTypeStyle>
                <sld:Rule>
                    <sld:RasterSymbolizer>
                        <sld:Opacity>1.0</sld:Opacity>
                        <sld:ColorMap>
                            <sld:ColorMapEntry color="#ffffff" opacity="0" quantity="-9999.0" label="nodata"/>
                            <sld:ColorMapEntry color="#A52A2A" quantity="-1.0" label="-1.0" opacity="1.0"/>
                            <sld:ColorMapEntry color="#E3BE0C" quantity="-0.302" label="-0.302" opacity="1.0"/>
                            <sld:ColorMapEntry color="#EFD907" quantity="-0.176" label="-0.176" opacity="1.0"/>
                            <sld:ColorMapEntry color="#FEFE00" quantity="-0.004" label="-0.004" opacity="1.0"/>
                            <sld:ColorMapEntry color="#F8FB00" quantity="0.027" label="0.027" opacity="1.0"/>
                            <sld:ColorMapEntry color="#ECF500" quantity="0.075" label="0.075" opacity="1.0"/>
                            <sld:ColorMapEntry color="#E0EF00" quantity="0.122" label="0.122" opacity="1.0"/>
                            <sld:ColorMapEntry color="#D8EB00" quantity="0.153" label="0.153" opacity="1.0"/>
                            <sld:ColorMapEntry color="#D2E800" quantity="0.176" label="0.176" opacity="1.0"/>
                            <sld:ColorMapEntry color="#C3E100" quantity="0.231" label="0.231" opacity="1.0"/>
                            <sld:ColorMapEntry color="#BCDD00" quantity="0.263" label="0.263" opacity="1.0"/>
                            <sld:ColorMapEntry color="#AAD400" quantity="0.333" label="0.333" opacity="1.0"/>
                            <sld:ColorMapEntry color="#A2D000" quantity="0.365" label="0.365" opacity="1.0"/>
                            <sld:ColorMapEntry color="#90C700" quantity="0.435" label="0.435" opacity="1.0"/>
                            <sld:ColorMapEntry color="#88C300" quantity="0.467" label="0.467" opacity="1.0"/>
                            <sld:ColorMapEntry color="#71B800" quantity="0.553" label="0.553" opacity="1.0"/>
                            <sld:ColorMapEntry color="#59AC00" quantity="0.647" label="0.647" opacity="1.0"/>
                            <sld:ColorMapEntry color="#409F00" quantity="0.749" label="0.749" opacity="1.0"/>
                            <sld:ColorMapEntry color="#269200" quantity="0.851" label="0.851" opacity="1.0"/>
                            <sld:ColorMapEntry color="#0C8500" quantity="0.953" label="0.953" opacity="1.0"/>
                            <sld:ColorMapEntry color="#008000" quantity="1.0" label="1.0" opacity="1.0"/>
                        </sld:ColorMap>
                    </sld:RasterSymbolizer>
                </sld:Rule>
            </sld:FeatureTypeStyle>
        </sld:UserStyle>
    </sld:NamedLayer>
</sld:StyledLayerDescriptor>