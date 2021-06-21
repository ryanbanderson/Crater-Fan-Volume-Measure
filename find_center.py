import matplotlib.pyplot as plot
import numpy as np

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


def circlefit(dem):
    global x,y
    x = []
    y = []
    plot.imshow(dem)
    ax = plot.gca()
    fig = plot.gcf()
    fig.suptitle('Click 10 points on the crater rim to fit with a circle:')

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