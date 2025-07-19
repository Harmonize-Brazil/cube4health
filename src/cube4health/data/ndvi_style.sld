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
                            <!-- Valor -1 (água/superfície não vegetada) em marrom -->
                            <sld:ColorMapEntry color="#654321" quantity="-1" label="-1" opacity="1.0"/>
                            <!-- Valor 0 (transição) em bege -->
                            <sld:ColorMapEntry color="#FFFFB2" quantity="0" label="0" opacity="1.0"/>
                            <sld:ColorMapEntry color="#006400" quantity="1" label="1" opacity="1.0"/>
                        </sld:ColorMap>
                    </sld:RasterSymbolizer>
                </sld:Rule>
            </sld:FeatureTypeStyle>
        </sld:UserStyle>
    </sld:NamedLayer>
</sld:StyledLayerDescriptor>