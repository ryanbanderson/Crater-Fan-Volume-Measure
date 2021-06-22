import matplotlib.pyplot as plot
import numpy as np

#Function to get x and y coordinates from the first 10 clicks, then close the image.
def onclick(event):
    x.append(event.xdata)
    y.append(event.ydata)
    print(len(x))

    xval = int(event.xdata)
    yval = int(event.ydata)
    print(str([xval,yval]))
    if len(x) == 10:
        event.canvas.mpl_disconnect(cid)
        print('DISCONNECT')
        plot.close()


'''
This script takes a DEM image as input, and allows the user to click 10 points along the rim. A circle is fit to the
points and the center coordinates are returned
'''
def circlefit(dem):
    #define x and y as global list variables
    global x,y
    x = []
    y = []

    #show the DEM
    plot.imshow(dem)
    ax = plot.gca()
    fig = plot.gcf()
    fig.suptitle('Click 10 points on the crater rim to fit with a circle:')

    #Set up to run the function onclick every time the user clicks the image
    global cid
    cid = fig.canvas.mpl_connect('button_press_event',onclick)
    plot.show()

    # define coordinates as arrays
    x = np.array(x)
    y = np.array(y)
    # create arrays used in circle calculation
    a1 = np.array([x, y, np.ones(np.shape(x))])
    a2 = np.array([-(x ** 2 + y ** 2)])

    # solve the least squares fit to get the center point
    a = np.linalg.lstsq(a1.T, a2.T, rcond=None)[0]
    xc = -0.5 * a[0]
    yc = -0.5 * a[1]

    return xc, yc