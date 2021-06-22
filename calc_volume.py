import os.path
import find_center
import skimage.io as io
import copy
import numpy as np
import dem_interp
import pandas as pd

#Writes the filled DEM to a GDAL file, borrowing properties from the original DEM
def write_gdal(demfile, filled, filledfile, nodataval = 32767):
    print('Saving '+filledfile)
    from osgeo import gdal
    dem = gdal.Open(demfile)
    band = dem.GetRasterBand(1)
    dem_arr = band.ReadAsArray()
    [cols,rows] = dem_arr.shape

    driver = gdal.GetDriverByName("GTiff")
    outdata = driver.Create(filledfile, rows, cols, 1, gdal.GDT_Int16)
    outdata.SetGeoTransform(dem.GetGeoTransform())##sets same geotransform as input
    outdata.SetProjection(dem.GetProjection())##sets same projection as input
    outdata.GetRasterBand(1).WriteArray(filled)
    outdata.GetRasterBand(1).SetNoDataValue(nodataval)##if you want these values transparent
    outdata.FlushCache()
    outdata = None

def get_masks(feature_files, bad_data = 32767):
    masks = {}
    for key in feature_files.keys():
        feature_dem_tmp = io.imread(feature_files[key])
        masks[key] = feature_dem_tmp == bad_data
    return masks

'''
This function calls the different methods for filling in the gaps in a DEM that has been 'clipped'

dem_clipped = DEM with areas that need to be filled in specified by the 'bad_data' value. This DEM should have *all*
              of the features in the crater masked, not just a single feature, so that areas with adjacent features
              are filled in correctly.
crater_center = Two-element list containing the x and y image coordinates of the center of the crater.
rsize = Number of radial steps to use when converting the image to polar coordinates
tsize = Number of angular steps to use when converting the image to polar coordinates
bad_data = Value interpreted as bad data. Default is the ArcGIS value of 32767.
method = Which interpolation method to use. See do_calc_vol for more details.
profile_type = Which type of profile to use if the method is 'profile'. See do_calc_vol for more details.
cratername = Name of the crater used in output files.
outpath = Directory in which to save results.
savefigs = Set to true to save png figures of the stages of the DEM filling.
               
'''
def fill_dem(dem_clipped, crater_center, rsize, tsize, bad_data = 32767, method = 'profile', profile_type = 'mean',
             cratername='crater', outpath='', savefigs=True):
    if method == 'annular':
        dem_filled = dem_interp.dem_interp_annular(dem_clipped, crater_center, rsize, tsize, bad_data_value=bad_data,
                                                   cratername=cratername, outpath=outpath, savefigs=savefigs)

    if method == 'radial':
        dem_filled = dem_interp.dem_interp_radial(dem_clipped, crater_center, rsize, tsize, bad_data_value=bad_data,
                                                  cratername=cratername,outpath=outpath,savefigs=savefigs)
    if method == 'cubic':
        dem_filled = dem_interp.dem_interp(dem_clipped, method=method, bad_data_value=bad_data,
                                           cratername=cratername,outpath=outpath,savefigs=savefigs)
    if method == 'linear':
        dem_filled = dem_interp.dem_interp(dem_clipped, method=method, bad_data_value=bad_data,
                                           cratername=cratername,outpath=outpath,savefigs=savefigs)
    if method == 'profile':
        dem_filled = dem_interp.dem_interp_profile(dem_clipped, crater_center,rsize, tsize, bad_data_value=bad_data,
                                                       profile_type=profile_type, cratername=cratername,
                                                        outpath=outpath,savefigs=savefigs)
    return dem_filled


'''
This script is the one that actually calculates the volumes.

dem = Original (non-clipped) DEM
dem_filled = DEM with clipped features filled in by one of the interpolation methods.
masks = Dict with masks for each feature, indicating which pixels in the DEM correspond to that feature
fan_catchment_match = Dict with keys for each fan and values for each corresponding catchment.
pixel_size = Physical size of the DEM pixels. Defaults to 20.0 meters. 
'''
def find_volumes(dem, dem_filled, masks, fan_catchment_match, pixel_size = 20.0):
    print('Calculating volumes. Pixel size: '+str(pixel_size))
    filled_fan = copy.copy(dem_filled)
    filled_catchment = copy.copy(dem_filled)

    # For fans, use original DEM values where fan is lower than the inferred surface
    filled_fan[dem < filled_fan] = dem[dem < filled_fan]
    diff_fan = dem - filled_fan

    # For catchments, use original DEM values where catchment is higher than the inferred surface
    filled_catchment[dem>filled_catchment]=dem[dem>filled_catchment]
    diff_catchment = filled_catchment - dem

    # Create empty dict to hold volumes
    volumes = {}
    # Get all feature names, mask names, and catchment names
    mask_keys = masks.keys()
    fans = fan_catchment_match.keys()
    catchments = [fan_catchment_match[key] for key in fan_catchment_match.keys()]

    #calculate volumes for each feature
    for key in mask_keys:
        if key in fans:
            volumes[key] = pixel_size*pixel_size*np.sum(diff_fan[masks[key]])/1e9
        elif key in catchments:
            volumes[key] = pixel_size*pixel_size*np.sum(diff_catchment[masks[key]])/1e9

    return diff_fan, diff_catchment, volumes


'''
Script for calculating the volume of catchments/fans in craters

Inputs: 
dem_file = File containing the original DEM
dem_clipped_file = File containing DEM with features to fill/measure "clipped" by setting to a nodata value
dem_feature_files = Dict containing DEM files with individual features clipped, and the corresponding names ("keys")
fan_catchment_match = Dict containing the names of fan features as keys and the name sof corresponding catchments as values
methods = List of methods to use for filling the DEM. Options include:
    'annular' = Topography is interpolated in annular rings 
    'radial' = Topography is interpolated radially
    'cubic' = Topography is interpolated using cubic interpolation (In my experience, tends to be slow and give crazy results...)
    'linear' = Topography is linearly interpolated (Also tends to be slow and gives iffy results...)
    'profile' = Topography is filled in based on a profile of the good data of the crater
profile_type = List of profile types. Must be the same length as the list of Methods, so fill with None to correspond with non-profile methods
    'median' = Profile calculated from the median of topography at each radial distance 
    'mean' = Profile calculated from the mean of topography at each radial distance
    'min' = Profile calculated from the min of topography at each radial distance
    'max' = Profile calculated from the max of topography at each radial distance
crater_center = coordinates in the DEM image of the crater center. If set to None, this will trigger find_center.py, 
                which lets the user click 10 points along the crater rim and fit a circle to get the center.
bad_data = Bad data value. Defaults to the ArcGIS default  of 32767
pixel_size = Spatial size of the DEM pixels, used to give volumes in physical units. Defaults to 20.0 meters.
outpath = Directory in which to save results.
cratername = Name of the crater used in output files.
savefigs = Set to true to save png figures of the stages of the DEM filling.
               

'''
def do_calc_vol(dem_file,dem_clipped_file, dem_feature_files, fan_catchment_match, methods, profile_type, crater_center=None,
                bad_data = 32767, pixel_size=20.0, outpath = '', cratername= 'crater', savefigs=True):

    dem = io.imread(dem_file)
    dem_clipped = io.imread(dem_clipped_file)
    feature_masks = get_masks(dem_feature_files)

    if cratername is None:
        cratername = 'crater'
    print('Calculating fan and catchment volumes for crater named: '+cratername)

    if crater_center == None:
        print('No crater center provided! Click 10 points to fit a circle and find the center.')
        crater_center = np.squeeze(find_center.circlefit(dem))
    print('Crater center is '+str(crater_center))

    results = pd.DataFrame(columns = ['crater','center_x','center_y','fan','fan_volume','catchment','catchment_volume','method','profile'])

    for i in np.arange(len(methods)):
        rsize = int(np.sqrt(crater_center[0] ** 2 + crater_center[1] ** 2))  # number of radial steps
        tsize = 1000  # number of angular steps

        print('Filling gaps using method: ' + methods[i])
        outstr = methods[i]
        if methods[i] == 'profile':
            print('Profile type: ' + profile_type[i])
            outstr = outstr + '_' + profile_type[i]

        dem_filled = fill_dem(dem_clipped, crater_center, rsize,tsize, bad_data=bad_data, method=methods[i],
                        profile_type=profile_type[i],cratername=cratername,outpath=outpath,savefigs=savefigs)

        #save the filled DEM with the same spatial information as the original DEM
        basename = os.path.basename(dem_clipped_file).split('.')[0]
        filledfile = outpath + basename + '_'+outstr + ".tif"
        write_gdal(dem_file, dem_filled, filledfile)

        #calculate the volumes using the difference between the original and filled DEMs
        diff_fan, diff_catchment, volumes = find_volumes(dem, dem_filled, feature_masks, fan_catchment_match,
                                                         pixel_size= pixel_size)

        #create a row of data for each fan/catchment pair for each method. Append it to the running list of results
        for key in fan_catchment_match:
            tmp = {'crater':[cratername],'center_x':[crater_center[0]],'center_y':[crater_center[1]],'fan':[key],
                   'fan_volume':[volumes[key]],'catchment':[fan_catchment_match[key]],'catchment_volume':[volumes[fan_catchment_match[key]]],
                   'method':[methods[i]],'profile':[profile_type[i]]}
            tmp_df = pd.DataFrame.from_dict(tmp)

            results = pd.concat((results,tmp_df))

    #save the results out to a .csv
    results.to_csv(outpath+cratername+'_cal_volume_results.csv')

    return results


######## Begin Example ##########
dem_file = r"E:\Work\Sinuous Ridges\DTMs\MOLA_HRSC_CTX_20190923_Harris_crop.tif"
dem_clipped_file = r"E:\Work\Sinuous Ridges\DTMs\MOLA_HRSC_CTX_20190923_Harris_clip_catchments_fans.tif"
dem_feature_files = {'SW_fan':r"E:\Work\Sinuous Ridges\DTMs\MOLA_HRSC_CTX_20190923_Harris_clip_fans_SW.tif",
                     'SSW_fan':r"E:\Work\Sinuous Ridges\DTMs\MOLA_HRSC_CTX_20190923_Harris_clip_fans_SSW.tif",
                     'NE_fan':r"E:\Work\Sinuous Ridges\DTMs\MOLA_HRSC_CTX_20190923_Harris_clip_fans_NE.tif",
                     'ENE_fan':r"E:\Work\Sinuous Ridges\DTMs\MOLA_HRSC_CTX_20190923_Harris_clip_fans_ENE.tif",
                     'ENE':r"E:\Work\Sinuous Ridges\DTMs\MOLA_HRSC_CTX_20190923_Harris_crop_catchment_clip_ENE.tif",
                     'NE':r"E:\Work\Sinuous Ridges\DTMs\MOLA_HRSC_CTX_20190923_Harris_crop_catchment_clip_NE.tif",
                     'SSW':r"E:\Work\Sinuous Ridges\DTMs\MOLA_HRSC_CTX_20190923_Harris_crop_catchment_clip_SSW.tif",
                     'SW':r"E:\Work\Sinuous Ridges\DTMs\MOLA_HRSC_CTX_20190923_Harris_crop_catchment_clip_SW.tif"}

fan_catchment_match = {'SW_fan':'SW',
                       'SSW_fan':'SSW',
                       'NE_fan':'NE',
                       'ENE_fan':'ENE'}
methods = ['annular', 'radial', 'profile','profile','profile','profile']#,'linear']
profile_type = [None, None, 'mean','median','min','max']#,'none']
outpath = r"E:\Work\Sinuous Ridges\DTMs\\"
cratername = 'debug'

do_calc_vol(dem_file,dem_clipped_file, dem_feature_files, fan_catchment_match, methods, profile_type, crater_center=None,
                bad_data = 32767, pixel_size=20.0, outpath = outpath,cratername=cratername, savefigs=True)