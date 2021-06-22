# Crater Fan Volume Measure
Scripts to estimate paleosurface and measure volume of craters with alluvial fans and catchments.

These scripts require a set of identically-sized DEMs for the crater of interest with the features over which to interpolate and estimate volume "clipped" out. Here are instructions for how to get the data files needed for the scrips using ArcMap. These instructions assume that you have already loaded your basemaps and DEMs, and that you have drawn polygons for the alluvial fans and catchments that you want to measure.

1. In ArcMap, zoom so that the crater of interest fills the field of view. Create a <a href="https://desktop.arcgis.com/en/arcmap/10.3/map/working-with-arcmap/using-spatial-bookmarks.htm">spatial bookmark</a> so that you can return to this exact view in the future if needed.
2. <a href="https://help.arcgis.com/en/arcgisdesktop/10.0/help/index.html#/Exporting_a_raster_in_ArcMap/009t00000063000000%20/">Export</a> DEM constrained to the current display extent.
3. <a href="https://resources.arcgis.com/en/help/main/10.1/index.html#//00s90000001v000000">Convert</a> fan and catchment polygons to graphics.
4. Select all fan and catchment graphics. <a hreaf="https://www.esri.com/arcgis-blog/products/product/analytics/clipping-an-image-or-raster-in-arcgis/">Export DEM using selected graphics, clipping inside.</a> This will create a clipped DEM, with data inside the fan and catchment polygons replaced with NoData.
5. Now repeat step 4 with each individual fan and catchment selected. This will create versions of the DEM with each feature clipped out, to be used later as masks to get the volume for each feature.
6. See the example in calc_volume.py which shows how to use these DEMs as input to the scripts.
