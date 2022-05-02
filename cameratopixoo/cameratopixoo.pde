/**
 * Telepulssi template for Processing.
 */

import java.util.*;
import java.net.*;
import java.io.*;

import java.text.*;
import processing.video.*;

Capture cam;
int i;

Divoom pixoo;

public void settings() {
  //System.setProperty("jogl.disable.openglcore", "true");
  size(16, 16);
}


void setup() {  
  // First set up your stuff.
  String[] cameras = Capture.list();
  
  if (cameras.length == 0) {
    println("There are no cameras available for capture.");
    exit();
  } else {
    println("Available cameras:");
    for (int i = 0; i < cameras.length; i++) {
      println(cameras[i]);
    }
    
    // The camera can be initialized directly using an 
    // element from the array returned by list():
    cam = new Capture(this,160,120, cameras[0]
    );
    cam.start();     
  }      
  
  noStroke();
     
  // If you supply serial port from command-line, use that. Emulate otherwise.
  Integer port = args == null ? null : parseInt(args[0]);
  pixoo = new Divoom(this, port == null, 1337); // Preview only
  frameRate(15);

  // Hide the original window
  surface.setVisible(false);
}

void draw() {
  if (cam.available() == true) {
    cam.read();
  }
  // Clear screen
  background(0);
  fill(255);

  pushMatrix();
  //rotateY(angle3);
  float ratio = (float)cam.width/(float)cam.height;
  int cwidth = (int)(height*ratio);
  int offsetx = (int)((cwidth-width)/2.0f);
  image(cam,-offsetx,0,cwidth,height);
  //drawLogo();
  popMatrix();

  // Finally update the screen and preview.
  pixoo.update();
  /*
  if(i<90){
    saveFrame("frame"+String.format("%04d",i)+".png");
  }
  i+=1;
  */
}
