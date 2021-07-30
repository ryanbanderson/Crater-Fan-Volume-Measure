import calc_volume

# The script requires several different versions of the DEM.
# These should be identical in size (# of pixels) and lat/lon extent.
# They are provided as paths to the DEM files.
#
# dem_file = Path to the original DEM, with nothing clipped
# dem_clipped_file = Path to the DEM with *all* catchments and fans clipped out. This is the file that will be interpolated.
#                    Interpolation is done with all features clipped to ensure that adjacent fans/catchments are handled correctly.
#                    (We want to interpolate to a non-fan elevation, not the elevation of the neighboring fan surface)
# dem_feature_files = A dictionary containing paths to versions of the DEM with each individual feature clipped.
#                     These are used as masks to calculate the volume for each feature individually.

dem_file = r"DEM.tif"  #If you just provide the file, Python will assume the file is in the same directory as the script.
                       # If the file is somewhere else, then provide the complete path.
                       # Make sure you have the r in front of the quotes so that python treats it as a "raw" string.
dem_clipped_file = r"DEM_clip_all.tif"

# For the dictionary, you provide a "key" and a "value" separated by a colon. The key should be a string used to
# identify the feature. The value should be the path to the file containing the DEM with that feature masked.
# This hypothetical example has two fans and two corresponding catchments.
dem_feature_files = {'Fan_1':"DEM_clip_fan1.tif",
                     'Catchment_1':"DEM_clip_catchment1.tif",
                     'Fan_2': "DEM_clip_fan2.tif",
                     'Catchment_2': "DEM_clip_catchment2.tif"
                     }

# This dictionary is used to tell the program which catchments match up with which fans,
# so that results can be written in the same row of the table.
fan_catchment_match = {'Fan_1':'Catchment_1',
                       'Fan_2':'Catchment_2'}

# The interpolation method(s) are specified in a list (square brackets). Annular is recommended!
# Linear and cubic are VERY slow and generally don't give great results.
methods = ['annular']#, 'radial', 'min','max','mean','median','linear','cubic']

outpath = r"E:\Work\Sinuous Ridges\DTMs\\" # Specify the directory where results will be saved
cratername = 'Example_Crater' # Specify the name of the crater, to be used in naming result files

# The coordinates of the center of the crater, in pixels in the DEM. If you don't know, you can set this to None.
# If this is None, the program will pop up an image of the crater and ask you to click 10 locations on the crater rim.
# These will be used to fit a circle and determine the crater center.
#crater_center = [1590, 1291]
crater_center = None

pixel_size = 20.0 #DEM pixel size in meters. Pixels are assumed to be square.

calc_volume.do_calc_vol(dem_file,dem_clipped_file, dem_feature_files, fan_catchment_match, methods, crater_center=crater_center,
                bad_data = 32767, pixel_size=pixel_size, outpath = outpath,cratername=cratername, savefigs=True)