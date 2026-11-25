"""fixture_prueba: escenas sintéticas exclusivas de validación de software."""
import cv2
import numpy as np


def scene(width=640,height=480,markers=True):
    image=np.full((height,width,3),235,np.uint8)
    cv2.rectangle(image,(width//9,height//3),(width//3,2*height//3),(20,30,220),-1)
    cv2.circle(image,(width//2,height//2),height//9,(20,190,25),-1)
    pts=np.array([[int(width*.7),int(height*.65)],[int(width*.9),int(height*.65)],[int(width*.8),int(height*.35)]])
    cv2.fillPoly(image,[pts],(220,70,20))
    if markers:
        dictionary=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        for i in range(3):
            side=max(32,width//9);x=width//10+i*width//3;y=height//20
            image[y:y+side,x:x+side]=cv2.cvtColor(cv2.aruco.generateImageMarker(dictionary,i,side),cv2.COLOR_GRAY2BGR)
    cv2.putText(image,'fixture_prueba',(10,height-12),cv2.FONT_HERSHEY_SIMPLEX,.6,(70,70,70),1,cv2.LINE_AA)
    return image
