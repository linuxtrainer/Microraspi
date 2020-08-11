from Tkinter import *
import tkMessageBox
import tkFileDialog
from PIL import Image
import picamera
import os
import math
import signal
import sys
from time import sleep
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw


global preview
preview=False

global xAddr # for motor-steps in x-direction(left/right)
xAddr=0
global yAddr # for motor-steps in y-direction (down/up)
yAddr=0
global X1point  # Rechtspunkt
X1point=None    
global X2point  # Linkspunkt
X2point=None
global Y1point  # Obenpunkt
Y1point=None
global Y2point  # Untenpunkt
Y2point=None
global yside
yside=None
global xside
xside=None
global xpichalf # Anzahl der Steps, die fuer einen halben Bildausschnitt in x-Richtung benoetigt werden.
xpichalf=None
global ypichalf # Anzahl der Steps, die fuer einen halben Bildausschnitt in y-Richtung benoetigt werden.
ypichalf=None
global anzpic
anzpic=None
global xAddr_mittel
xAddr_mittel=None
global yAddr_mittel
yAddr_mittel=None
global correction  # bei Richtungswechsel gibt einen einen gewissen mechanischen Spielraum, bis das
correction=80 #110 # Praeparat wieder bewegt wird. Hier die Anzahl der Steps, die der Leerlauf verbraucht

home=os.getenv("HOME")
global initialimagedir
initialimagedir=home+'/Bilder'
imagefile="image1.jpg"
global initialbasename
initialbasename="mikro_"

# wichtig
# Mikroskop Biolam Nr.730842 ergibt folgende Parameter:
# eine vollstaendige Umdrehung Kreuztisch in rechts/Links Richtung ergibt eine Verschiebung um 2.1mm
# fuer den Step-Motor 28BYJ-48  ergibt dies fuer einen Step 4.1 Mikrometer
#
# eine vollstaendige Umdrehung Kreuztisch in rauf/runter(vor/zurueck) Richtung ergibt eine Verschiebung um 15.8mm
# fuer den Step-Motor 28BYJ-48  ergibt dies fuer einen Step 31 Mikrometer
#


#
#  start-point                                   xside
#  Startpunkt    cyclus_forward(1) -->         Rechtspunkt
#     x ------------------------------------------ x
#     |   <--cyclus_backward(1)
# c   |  A
# y   |  |
# c   |  |
# l   |  c
# u   |  y
# s   |  c
# _   |  l
# b   |  u
# a   |  s
# c   |  _
# k   |  f
#(0)  |  o
# |   |  r
# |   | (0)
# V   |
#     x
#   Downpunkt
#    yside


# Use BCM GPIO references instead of physical pin numbers
GPIO.setmode(GPIO.BCM)

# die verwendeten Pins am raspberry
StepPins = [18,23,24,25,17,27,22,4]

# Set all pins as output an define them low
for pin in StepPins:
    GPIO.setup(pin,GPIO.OUT)
    GPIO.output(pin,False)



def step(w1,w2,w3,w4,motor):
    if motor == 0:
       pinA = 18   # Number 12
       pinB = 23   # Number 16
       pinC = 24   # Number 18
       pinD = 25   # Number 22
       zeit = 0.01 # motor 0 needs more power, interval must be high
    else:          # motor will be slower
       pinA = 17    # Number 11
       pinB = 27    # Number 13
       pinC = 22    # Number 15
       pinD = 4     # Number 7
       #zeit = 0.001 # motor 1 needs not a lot of power, but speed is needed
       zeit = 0.002 # motor 1 needs not a lot of power, but speed is needed

    GPIO.output(pinA,w1)
    GPIO.output(pinB,w2)
    GPIO.output(pinC,w3)
    GPIO.output(pinD,w4)
    sleep(zeit)
    GPIO.output(pinA,False)
    GPIO.output(pinB,False)
    GPIO.output(pinC,False)
    GPIO.output(pinD,False)


def cyclus_forward(motor,walks):      # eight steps is one cyclus, 512 cyclus makes the
    for i in range(walks):            # motor do a full rotation.
        if motor==1:
           global xAddr
           xAddr += 1
        else:
           global yAddr
           yAddr -= 1
        step(False,False,False,True,motor)
        step(False,False,True,True,motor)
        step(False,False,True,False,motor)
        step(False,True,True,False,motor)
        step(False,True,False,False,motor)
        step(True,True,False,False,motor)
        step(True,False,False,False,motor)
        step(True,False,False,True,motor)
        print "xAddr:",xAddr," yAddr:",yAddr


def cyclus_backward(motor,walks):
    for i in range(walks):
        if motor==1:
           global xAddr
           xAddr -= 1
        else:
           global yAddr
           yAddr += 1
        step(True,False,False,True,motor)
        step(True,False,False,False,motor)
        step(True,True,False,False,motor)
        step(False,True,False,False,motor)
        step(False,True,True,False,motor)
        step(False,False,True,False,motor)
        step(False,False,True,True,motor)
        step(False,False,False,True,motor)
        print "xAddr:",xAddr," yAddr:",yAddr


def fix_positions(point):
    global xAddr
    global yAddr
    global X1point
    global X2point
    global Y1point
    global Y2point
    if point=='Xrechts':
       X1point=xAddr
       print "Rechtspunkt: ",X1point
    if point=='Xlinks':
       X2point=xAddr
       print "Linkspunkt: ",X2point
    if point=='Yoben':
       Y1point=yAddr
       print "Obenpunkt: ",Y1point
    if point=='Yunten':
       Y2point=yAddr
       print "Untenpunkt: ",Y2point


def fix_mittelpunkt():
    global xAddr
    global yAddr
    global xAddr_mittel
    global yAddr_mittel
    xAddr_mittel=xAddr
    yAddr_mittel=yAddr
    print "Mittelpunkt: ",xAddr_mittel,yAddr_mittel


def set_anzahlpic():
    global anzpic
    if anzahlpic.get() == 1:
        anzpic=50
        print "Anzahl Bilder: ",anzpic
    if anzahlpic.get() == 2:
        anzpic=100
        print "Anzahl Bilder: ",anzpic
    if anzahlpic.get() == 3:
        anzpic=300
        print "Anzahl Bilder: ",anzpic
    if anzahlpic.get() == 4:
        anzpic=500
        print "Anzahl Bilder: ",anzpic
    if anzahlpic.get() == 5:
        anzpic=700
        print "Anzahl Bilder: ",anzpic


def calc_quadrat():
    global anzpic
    global xAddr_mittel
    global yAddr_mittel
    global xpichalf
    global ypichalf
    global X1point
    global X2point
    global Y1point
    global Y2point
    numberpic=int(round(math.sqrt(anzpic)))
    X2point=int(-(numberpic/2*xpichalf)+xAddr_mittel)
    X1point=int((numberpic/2*xpichalf)+xAddr_mittel)
    Y1point=int(-(numberpic/2*ypichalf)+yAddr_mittel)
    Y2point=int((numberpic/2*ypichalf)+yAddr_mittel)


def calc_window():
    global xAddr
    global yAddr
    global xside
    global yside
    if xpichalf==None or ypichalf==None:
       tkMessageBox.showerror("Objektiv","Noch kein Objektiv definiert. Bitte Objektiv auswaehlen.")
       return 1
    if anzpic != None and xAddr_mittel != None and yAddr_mittel != None:
       calc_quadrat();
       print "Quadrat wurde definiert ueber Mittelpunkt"
    else:
       print "Kein Quadrat definiert" 
    if X1point != None and X2point != None and Y1point != None and Y2point != None:
       xside=abs(X1point-X2point)
       yside=abs(Y1point-Y2point)
       print "xside:",xside,"yside:",yside
       return 0
    else:
       print "Fehler in calc_window"
       retval=' '
       if X1point == None:
          retval=retval+'X-rechts '
       if X2point == None:
          retval=retval+'X-links '
       if Y1point == None:
          retval=retval+'Y-oben '
       if Y2point == None:
          retval=retval+'Y-unten '
       return retval


def goto_pos(xpos,ypos):
    if xAddr>xpos:
       cyclus_backward(1,abs(xpos-xAddr))
    if xAddr<xpos:
       cyclus_forward(1,abs(xpos-xAddr))
    if yAddr>ypos:
       cyclus_forward(0,abs(ypos-yAddr))
    if yAddr<ypos:
       cyclus_backward(0,abs(ypos-yAddr))


def goto_start():
    retval=calc_window()
    if retval==0:
       goto_pos(X2point,Y1point)
       return retval
    else:
       tkMessageBox.showerror("Punkt fehlt","Folgende Punkte noch nicht definiert: %s " % retval)
       return retval


def mk_singlepics(withpic): # moves object half the size of image-width
    if xpichalf==None or ypichalf==None:
       tkMessageBox.showerror("Objektiv","Noch kein Objektiv definiert. Bitte Objektiv auswaehlen.")
       return 1
    retval=goto_start()
    print "retval von goto_start: ",retval
    if retval!=0:
       print "Problem in mk_singlepics: ", retval
       return 0
    direction=1 # first go right
    if withpic=='on':
       #preview_off()
       number=1
       basename=tkFileDialog.asksaveasfilename(initialdir=initialimagedir,initialfile=initialbasename)

    for y in range(0,yside,ypichalf):    # always move size of half picture
        for x in range(0,xside,xpichalf):# then take picture
            if direction==1:
               cyclus_forward(1,xpichalf)
            if direction==0:
               cyclus_backward(1,xpichalf)
            print "direction:",direction," xside:",xside," yside:",yside,"xAddr:",xAddr,"yAddr:",yAddr
            #sleep(5)
            check_signal
            master.protocol("WM_DELETE_WINDOW",quit_prog)
            if withpic=='on':     # when withpic is on, pitures are taken, withpic is off
                                  # is used for simulation
               # Hier Einzelaufnahme ausloesen
               number += 1
               filename=basename+str(number)+'.jpg'
               sleep(1)
               take_picture(filename)
               print 'Taken picture:',filename
            sleep(1)

        cyclus_backward(0,ypichalf)
        # only for debug
        #if withpic=='on': # when change the direction, image is created to mark this
        #    number += 1
        #    filename=basename+str(number)+'.jpg'
        #    img = Image.new('RGB', (400, 100), color = (73, 109, 137))
        #    d = ImageDraw.Draw(img)
        #    d.text((10,10), "Richtungswechsel", fill=(255,255,0))
        #    img.save(filename)
        # Ende - only for debug
        if direction==1:
           direction=0
           cyclus_backward(1,correction)
        else:
           direction=1
           cyclus_forward(1,correction)


def mk_testpic():
    basename=tkFileDialog.asksaveasfilename(initialdir=initialimagedir,initialfile=initialbasename)
    filename=basename+'.jpg'
    take_picture(filename)


def set_objectiv():
    global xpichalf
    global ypichalf
    if objectiv.get() == 1:
       xpichalf=150
       ypichalf=18
    if objectiv.get() == 2: #10
       xpichalf=50
       ypichalf=6
       #xpichalf=72
       #ypichalf=8
    if objectiv.get() == 3: # 20
       #xpichalf=32
       xpichalf=40
       ypichalf=5
    if objectiv.get() == 4: #25
       #xpichalf=32
       xpichalf=32
       ypichalf=5
    if objectiv.get() == 5: # 30
       xpichalf=24
       ypichalf=3
    if objectiv.get() == 6: # 40
       xpichalf=24
       ypichalf=3
    print_values()


def print_values(): # print current image-values in to top-window
    textw.delete('1.0','2.114') # zurst alles loeschen von Position 1.0 bis 2.114 (Zeile/Spalte)
    textw.insert('1.0','exposure_speed:'+str(camera.exposure_speed)+'|'+'shutter_speed:'+str(camera.shutter_speed)+'|'
    +'fps:'+str(camera.framerate)+'|'+'contrast:'+str(camera.contrast)+'|'+'exposure_compensation:'+str(camera.exposure_compensation)+'|'
    +'brightness:'+str(camera.brightness)+'|'+'awb_gains (red/blue):'+str(camera.awb_gains)+'|'+'saturation:'+str(camera.saturation)+'|'
    +'sharpness:'+str(camera.sharpness)+'|'+'xpichalf:'+str(xpichalf)+'|'+'ypichalf:'+str(ypichalf))


def set_values(): # set values which will used for taking pictures
    camera.iso=w6.get()
    #camera.exposure_mode='off' #exposure_mode sollte nicht deaktiviert werden, verursacht grosse Probleme (schwarze Bilder)
    camera.awb_mode='off'
    sspeed=w3.get()
    camera.shutter_speed=sspeed # integer,microseconds, 1000000=eine Sekunde!
    fps=1000000/sspeed
    if fps>50:
       fps=50
    camera.framerate=fps # wichtig wenn exposure_mode auf off
    camera.awb_gains=(w1.get(),w2.get())
    camera.brightness=w4.get()
    camera.contrast=w5.get()
    #camera.exposure_compensation=w9.get()
    camera.saturation=w7.get()
    camera.sharpness=w8.get()
    camera.drc_strength='high'
    print_values()


def set_default(): # set camera-values back to default values, as defined when programm is started
    w1.set(3.0)    # awb red
    w2.set(1.3)    # awb blue
    w3.set(90000)  # shutter speed
    w4.set(50)     # brightness
    w5.set(0)      # contrast
    w6.set(50)     # iso
    w7.set(0)      # saturation
    w8.set(0)      # sharpness
    camera.rotation=0
    set_values()


def take_picture(picfile): # take one image from still-port of camera
    camera.stop_preview()  # picfile is name of file with full path
    #camera.resolution=(320,240)
    #camera.resolution=(2592,1944)
    camera.resolution=(4056,3040)
    #camera.image_denoise=True
    sleep(1)
    try:
       camera.capture(picfile,format='jpeg',resize=None,quality=100)
       #camera.capture(picfile,format='jpeg',resize=None,quality=100,bayer=True)
       #tkMessageBox.showinfo("Create file","Image %s successful created!" % picfile)
       print_values()
       if preview:
          preview_on()
    except:
       tkMessageBox.showerror("Create file","Error create file: %s" % picfile)
       if preview:
          preview_on()


def show_picture(): # for diplaying image to the screen
    try:
       preview_off()
       basename=tkFileDialog.askopenfilename(initialdir=initialimagedir,initialfile='mikro.jpg')
       image=Image.open(basename)
       image.show()
       if preview==True:
          preview_on()
    except:
       preview_off()
       tkMessageBox.showwarning("Open file","Cannot open this file: %s" % picfile)
       if preview==True:
          preview_on()


def preview_on():
    camera.preview_fullscreen=False
    camera.start_preview()
    #print "psize.get", psize.get()
    if psize.get() == 0:
        tkMessageBox.showerror("Preview","Groesse fuer das Vorschaufenster nicht gesetzt")
    if psize.get() == 1:
        #camera.exposure_mode='auto'
        camera.resolution=(640,480)
        #camera.preview.alpha=200
        camera.preview_fullscreen=False
        camera.preview_window=(0,0,640,480)
    if psize.get() == 2:
        #camera.exposure_mode='auto'
        camera.resolution=(1280,960)
        #camera.preview.alpha=200
        camera.preview_fullscreen=False
        camera.preview_window=(0,0,1280,960)
    if psize.get() == 3:
        #camera.exposure_mode='auto'
        camera.resolution=(1800,1350)
        #camera.preview.alpha=200
        camera.preview_fullscreen=False
        camera.preview_window=(0,0,1800,1350)
    global preview
    preview=True


def preview_off():
    camera.stop_preview()
    global preview
    preview=False


def p_update():
    #print "preview:",preview
    if preview:
          preview_on()
          
          
def quit_prog():
    master.destroy()
    camera.stop_preview()
    GPIO.cleanup()
    camera.close()


def receive_signal(signum,stack):
    print 'Received:',signum


def check_signal():
    signal.signal(signal.SIGHUP,receive_signal)
    signal.signal(signal.SIGINT,receive_signal)
    signal.signal(signal.SIGUSR1,receive_signal)
    signal.signal(signal.SIGUSR2,receive_signal)
    signal.signal(signal.SIGQUIT,receive_signal)
    signal.signal(signal.SIGTERM,receive_signal)


camera = picamera.PiCamera()
master=Tk()
#master.geometry('+640+100')
master.geometry('800x1030+1100+10')

objectiv=IntVar()
psize=IntVar()
anzahlpic=IntVar()

textw=Text(master,height=2,width=114)
textw.pack()

previewframe=Frame(master,relief='sunken',border=1)
picframe=Frame(master)
fixpositionframe=Frame(master,relief='groove',border=1)
sequenceframe=Frame(master,relief='sunken',border=1)
radioframe=Frame(master,relief='sunken',border=1)
anzahlframe=Frame(master,relief='groove',border=1)
psizeframe=Frame(master,relief='sunken',border=1)
motorframe=Frame(master)
anwendframe=Frame(master)

motorframe.pack(side=TOP)
fixpositionframe.pack(side=TOP,fill='x')
sequenceframe.pack(side=TOP,fill='x')
psizeframe.pack(side=TOP,fill='x')
previewframe.pack(side=BOTTOM,fill='x')
anwendframe.pack(side=BOTTOM)
radioframe.pack(fill='x') # fuer die Objektivzuordnung
anzahlframe.pack(fill='x')


w1=Scale(master,from_=0,to=8,resolution=0.1,length=800,orient=HORIZONTAL,border=0,label='awb red')
w1.set(1.0)
w1.pack()
w2=Scale(master,from_=0,to=8,resolution=0.1,length=800,orient=HORIZONTAL,border=0,label='awb blue')
w2.set(1.0)
w2.pack()
w3=Scale(master,from_=20000,to=1000000,resolution=5000,length=800,orient=HORIZONTAL,border=0,label='shutter speed')
w3.set(30000)
w3.pack()
w4=Scale(master,from_=0,to=100,length=800,orient=HORIZONTAL,border=0,label='brightness')
w4.set(50)
w4.pack()
w5=Scale(master,from_=-100,to=100,length=800,orient=HORIZONTAL,border=0,label='contrast')
w5.set(0)
w5.pack()
#w9=Scale(master,from_=-25,to=25,length=800,orient=HORIZONTAL,border=0,label='exposure_compensation')
#w9.set(0)
#w9.pack()
w6=Scale(master,from_=50,to=800,resolution=50,length=800,orient=HORIZONTAL,border=0,label='iso')
w6.set(100)
w6.pack()
w7=Scale(master,from_=-100,to=100,length=800,orient=HORIZONTAL,border=0,label='saturation')
w7.set(0)
w7.pack()
w8=Scale(master,from_=-100,to=100,length=800,orient=HORIZONTAL,border=0,label='sharpness')
w8.set(0)
w8.pack()

Radiobutton(radioframe,text="Objektiv 3.5",variable=objectiv,value=1,command=set_objectiv).pack(side=LEFT,anchor=W)
Radiobutton(radioframe,text="Objektiv 10",variable=objectiv,value=2,command=set_objectiv).pack(side=LEFT,anchor=W)
Radiobutton(radioframe,text="Objektiv 20",variable=objectiv,value=3,command=set_objectiv).pack(side=LEFT,anchor=W)
Radiobutton(radioframe,text="Objektiv 25",variable=objectiv,value=4,command=set_objectiv).pack(side=LEFT,anchor=W)
Radiobutton(radioframe,text="Objektiv 30",variable=objectiv,value=5,command=set_objectiv).pack(side=LEFT,anchor=W)
Radiobutton(radioframe,text="Objektiv 40",variable=objectiv,value=6,command=set_objectiv).pack(side=LEFT,anchor=W)

Radiobutton(anzahlframe,text="50",variable=anzahlpic,value=1,command=set_anzahlpic).pack(side=LEFT,anchor=W)
Radiobutton(anzahlframe,text="100",variable=anzahlpic,value=2,command=set_anzahlpic).pack(side=LEFT,anchor=W)
Radiobutton(anzahlframe,text="300",variable=anzahlpic,value=3,command=set_anzahlpic).pack(side=LEFT,anchor=W)
Radiobutton(anzahlframe,text="500",variable=anzahlpic,value=4,command=set_anzahlpic).pack(side=LEFT,anchor=W)
Radiobutton(anzahlframe,text="700",variable=anzahlpic,value=5,command=set_anzahlpic).pack(side=LEFT,anchor=W)
Button(anzahlframe,text='Quadratmittelpunk festlegen',command=fix_mittelpunkt).pack(side=RIGHT,padx=10,pady=20)

Button(fixpositionframe,text='X-rechts festlegen',command=lambda: fix_positions('Xrechts')).pack(side=RIGHT,padx=10,pady=20)
Button(fixpositionframe,text='X-links festlegen',command=lambda: fix_positions('Xlinks')).pack(side=LEFT,padx=10,pady=20)
Button(fixpositionframe,text='Y-oben festlegen',command=lambda: fix_positions('Yoben')).pack(side=TOP,padx=10,pady=20)
Button(fixpositionframe,text='Y-unten festlegen',command=lambda: fix_positions('Yunten')).pack(side=BOTTOM,padx=10,pady=20)
Button(sequenceframe,text='Dry-run',command=lambda: mk_singlepics('off')).grid(row=0,column=0)
Button(sequenceframe,text='Einzelaufnahmen starten',command=lambda: mk_singlepics('on')).grid(row=0,column=1)
Button(sequenceframe,text='Goto Start',command=goto_start).grid(row=0,column=3)
Button(anwendframe,text='Aenderungen uebernehmen',command=set_values).pack(side=LEFT)
Button(anwendframe,text='Alle Werte auf default',command=set_default).pack(side=RIGHT)

Radiobutton(psizeframe,text='640x480',variable=psize,value=1,command=p_update).pack(side=LEFT,anchor=W)
Radiobutton(psizeframe,text='1280x960',variable=psize,value=2,command=p_update).pack(side=LEFT,anchor=W)
Radiobutton(psizeframe,text='1800x1350',variable=psize,value=3,command=p_update).pack(side=LEFT,anchor=W)

Button(previewframe,text='Vorschau starten',command=preview_on).pack(side=LEFT,pady=10)
Button(previewframe,text='Bild aufnehmen',command=mk_testpic).pack(side=LEFT,pady=10)
Button(previewframe,text='Bild anzeigen',command=show_picture).pack(side=LEFT,pady=10)
Button(previewframe,text='Vorschau beenden',command=preview_off).pack(side=LEFT,pady=10)
Button(previewframe,text='Programm beenden',foreground='red',command=quit_prog).pack(side=RIGHT,pady=10)

Button(motorframe,text='>',repeatdelay=100,repeatinterval=3,command=lambda: cyclus_forward(1,1)).pack(side=RIGHT,padx=10,pady=20)
Button(motorframe,text='<',repeatdelay=100,repeatinterval=3,command=lambda: cyclus_backward(1,1)).pack(side=LEFT,padx=10,pady=20)
Button(motorframe,text=' /\ ',repeatdelay=100,repeatinterval=20,command=lambda: cyclus_forward(0,1)).pack(side=TOP,padx=10,pady=20)
Button(motorframe,text='V',repeatdelay=100,repeatinterval=20,command=lambda: cyclus_backward(0,1)).pack(side=BOTTOM,padx=10,pady=20)



set_default()
set_values()
master.protocol("WM_DELETE_WINDOW",quit_prog)

mainloop()


GPIO.cleanup()
camera.close()
