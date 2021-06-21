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

def find_volumes(dem, dem_filled, masks, fan_catchment_match, pixel_size = 20.0):
    print('Calculating volumes. Pixel size: '+str(pixel_size))
    filled_fan = copy.copy(dem_filled)
    filled_catchment = copy.copy(dem_filled)

    # use DEM values where fan is lower than the inferred surface
    filled_fan[dem < filled_fan] = dem[dem < filled_fan]
    diff_fan = dem - filled_fan

    # use DEM values where catchment is higher than the inferred surface
    filled_catchment[dem>filled_catchment]=dem[dem>filled_catchment]
    diff_catchment = filled_catchment - dem

    volumes = {}
    mask_keys = masks.keys()

    fans = fan_catchment_match.keys()

    catchments = [fan_catchment_match[key] for key in fan_catchment_match.keys()]
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
methods = List of methods to use for filling the DEM. Options include:
    'annular' = Topography is interpolated in annular rings 
    'radial' = Topography is interpolated radially
    'cubic' = Topography is interpolated using cubic interpolation (In my experience, tends to be slow and give crazy results...)
    'linear' = Topography is linearly interpolated
    'profile' = Topography is filled in based on a profile of the good data of the crater
profile_type = List of profile types. Must be the same length as the list of Methods, so fill with None to correspond with non-profile methods
    'median' = Profile calculated from the median of topography at each radial distance 
    'mean' = Profile calculated from the mean of topography at each radial distance
    'min' = Profile calculated from the min of topography at each radial distance
    'max' = Profile calculated from the max of topography at each radial distance
name = 
crater_center =
bad_data = 
outpath =
filled_file_base = 

dem_files = Structure containing the full dem, clipped dem, and dems with individual features clipped. For example:
    dem_files = {'dem': r"D:\Work\Sinuous Ridges\DTMs\MOLA_HRSC_CTX_20190923_7.tif",
                    'clipped': r"D:\Work\Sinuous Ridges\DTMs\MOLA_HRSC_CTX_20190923_7_clip_catchments_fans.tif",
                    'E': r"D:\Work\Sinuous Ridges\DTMs\MOLA_HRSC_CTX_20190923_7_catchment_clip_E.tif",
                    'E_fan': r"D:\Work\Sinuous Ridges\DTMs\MOLA_HRSC_CTX_20190923_7_clip_fans_E.tif",}
                

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

        basename = os.path.basename(dem_clipped_file).split('.')[0]
        filledfile = outpath + basename + '_'+outstr + ".tif"
        write_gdal(dem_file, dem_filled, filledfile)

        diff_fan, diff_catchment, volumes = find_volumes(dem, dem_filled, feature_masks, fan_catchment_match,
                                                         pixel_size= pixel_size)

        for key in fan_catchment_match:
            tmp = {'crater':[cratername],'center_x':[crater_center[0]],'center_y':[crater_center[1]],'fan':[key],
                   'fan_volume':[volumes[key]],'catchment':[fan_catchment_match[key]],'catchment_volume':[volumes[fan_catchment_match[key]]],
                   'method':[methods[i]],'profile':[profile_type[i]]}
            tmp_df = pd.DataFrame.from_dict(tmp)

            results = pd.concat((results,tmp_df))

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