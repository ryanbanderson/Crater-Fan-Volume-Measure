import numpy as np
import scipy.interpolate as interp
import copy
import matplotlib.pyplot as plot
import cv2


def save_dem_fig (dem_to_save, name, outpath, bad_data_value = 32767):
    dem_for_fig = copy.deepcopy(dem_to_save)
    dem_for_fig[dem_for_fig == bad_data_value] = np.max(dem_for_fig[dem_for_fig != bad_data_value])
    plot.imsave(outpath+name, dem_for_fig)
    plot.close()

def dem_interp(dem_with_holes, bad_data_value = 32767, method = 'cubic', cratername = 'crater', outpath='', savefigs = True):
    if savefigs: save_dem_fig(dem_with_holes, cratername + '_with_holes.png', outpath, bad_data_value=bad_data_value)
    mask = dem_with_holes == bad_data_value
    fill = interp.griddata(np.where(~mask), dem_with_holes[~mask], np.where(mask), method = method)
    dem_filled = copy.copy(dem_with_holes)
    dem_filled[mask] = fill
    if savefigs: save_dem_fig(dem_filled, cratername + '_filled_'+method+'.png', outpath, bad_data_value=bad_data_value)

    return dem_filled

def dem_interp_annular(dem_with_holes,center, rsize, tsize, bad_data_value = 32767, cratername = 'crater', outpath= '',  savefigs = True):
    if savefigs: save_dem_fig (dem_with_holes, cratername+'_with_holes.png', outpath, bad_data_value = bad_data_value)

    #"unwrap" the image into a rectangle where the axes are theta, radius
    polar_img = cv2.warpPolar(dem_with_holes,(rsize, tsize),(center[0], center[1]), maxRadius=rsize, flags=cv2.INTER_NEAREST)

    if savefigs: save_dem_fig(polar_img, cratername+'_polar.png', outpath, bad_data_value=bad_data_value)

    for r in np.arange(polar_img.shape[1]):
        annulus = polar_img[:,r]  #get one annulus
        bad_data = annulus == bad_data_value  #flag bad data in the annulus

        #get x coordinates of good/bad data for interpolation
        xcoords = np.arange(annulus.size)
        xcoords_good = xcoords[~bad_data]
        xcoords_bad = xcoords[bad_data]

        #if there is bad data, fill it in by interpolation
        if np.sum(bad_data)>0:
            if len(xcoords_good) >5:
                annulus[bad_data] = np.interp(xcoords_bad,xcoords_good,annulus[~bad_data],period = polar_img.shape[0])
            else:
                #if the entire annulus is bad data, fill it in with the previous annulus
                print('no good data! Use the previous annulus')
                annulus = polar_img[:,r-1]
                pass
            polar_img[:,r] = annulus

    #re-wrap the filled image back to x,y coordinates
    dem_filled = cv2.warpPolar(polar_img,dem_with_holes.shape[::-1],(center[0],center[1]),maxRadius=rsize, flags=cv2.INTER_NEAREST+cv2.WARP_INVERSE_MAP)

    if savefigs: save_dem_fig(dem_filled, cratername+'_filled_annular.png', outpath, bad_data_value=bad_data_value)

    return dem_filled

def dem_interp_radial(dem_with_holes,center, rsize, tsize, bad_data_value = 32767, cratername = 'crater', outpath= '',  savefigs = True):
    if savefigs: save_dem_fig(dem_with_holes, cratername + '_with_holes.png', outpath, bad_data_value=bad_data_value)

    #"unwrap" the image into a rectangle where the axes are theta, radius
    polar_img = cv2.warpPolar(dem_with_holes,(rsize, tsize),(center[0], center[1]), maxRadius=rsize, flags=cv2.INTER_NEAREST)
    if savefigs: save_dem_fig(dem_with_holes, cratername + '_polar.png', outpath, bad_data_value=bad_data_value)

    for t in np.arange(polar_img.shape[0]):
        radius = polar_img[t,:]
        bad_data = radius == bad_data_value
        xcoords = np.arange(radius.size)
        xcoords_good = xcoords[~bad_data]
        xcoords_bad = xcoords[bad_data]
        if np.sum(bad_data)>0:
            if len(xcoords_good) >0:
                radius[bad_data] = np.interp(xcoords_bad,xcoords_good,radius[~bad_data],period = polar_img.shape[1])
            else:
                pass
            polar_img[t,:] = radius


    #re-wrap the filled image back to x,y coordinates
    dem_filled = cv2.warpPolar(polar_img,dem_with_holes.shape[::-1],(center[0],center[1]),maxRadius=rsize, flags=cv2.INTER_NEAREST+cv2.WARP_INVERSE_MAP)
    if savefigs: save_dem_fig(dem_filled, cratername + '_filled_radial.png', outpath, bad_data_value=bad_data_value)

    return dem_filled


def dem_interp_profile(dem_with_holes, center, rsize, tsize, bad_data_value = 32767, profile_type = 'mean', cratername='',
                       outpath='',savefigs=True):
    if savefigs: save_dem_fig(dem_with_holes, cratername + '_with_holes.png', outpath, bad_data_value=bad_data_value)
    mask = dem_with_holes == bad_data_value

    #"unwrap" the image into a rectangle where the axes are theta, radius
    polar_img = cv2.warpPolar(dem_with_holes,(rsize, tsize),(center[0], center[1]), maxRadius=rsize, flags=cv2.INTER_NEAREST)
    if savefigs: save_dem_fig(dem_with_holes, cratername + '_polar.png', outpath, bad_data_value=bad_data_value)

    polar_img = polar_img.astype(float)
    polar_img[polar_img == bad_data_value] = np.nan
    if profile_type == 'median':
        profile = np.nanmedian(polar_img, axis=0)
    if profile_type == 'mean':
        profile = np.nanmean(polar_img, axis=0)
    if profile_type == 'min':
        profile = np.nanmin(polar_img,axis = 0)
    if profile_type == 'max':
        profile = np.nanmax(polar_img,axis=0)

    #extend the profile to fill rectangle
    profile_img = np.array(np.tile(profile, (tsize,1)),dtype=int)

    #re-wrap the profile image back to x,y coordinates
    profile_dem = cv2.warpPolar(profile_img,dem_with_holes.shape[::-1],(center[0],center[1]),maxRadius=rsize, flags=cv2.INTER_NEAREST+cv2.WARP_INVERSE_MAP)

    #fill in the holes with values from the profile image
    dem_filled = copy.copy(dem_with_holes)
    dem_filled[mask] = profile_dem[mask]

    if savefigs: save_dem_fig(dem_filled, cratername + '_filled_'+profile_type+'.png', outpath, bad_data_value=bad_data_value)

    return dem_filled