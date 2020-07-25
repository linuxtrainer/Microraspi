from Tkinter import *
import picamera
import tkFileDialog
import tkMessageBox
import tkSimpleDialog
import os
from time import sleep
import RPi.GPIO as GPIO
import numpy
from scipy.misc import imread, imsave
from PIL import Image
import cv2
import threading
import thread


preview=False
home=os.getenv("HOME")
initialimagedir=home+'/Bilder'
imagefile="image1.jpg"
initialbasename="mikro_"
initialflatname="flat_"
flatfieldname='none'
hdrflatfilenames=[]
flatokay=False
hdrproductname=initialimagedir+"/"+initialbasename
hdrfilenames=[]
speeds=[]
speedssec=[]
threads=[]


class MyThread (threading.Thread):
        def __init__(self,threadID,name,flatokay,hdrfilenames,hdrflatfilenames,hdrproductname,speedssec):
            threading.Thread.__init__(self)
            self.threadID = threadID
            self.name = name
            self.flatokay = flatokay      
            self.hdrfilenames = hdrfilenames
            self.hdrflatfilenames = hdrflatfilenames
            self.hdrproductname = hdrproductname
            self.speedssec = speedssec
        def run(self):
            print ("Starting " + self.name)
            print self.hdrfilenames,self.hdrproductname
            bake_hdr(self.flatokay,self.hdrfilenames,self.hdrflatfilenames,self.hdrproductname,speedssec)
            print ("Exiting " + self.name)


def print_values(): # print current image-values in to top-window
    textw.delete('1.0','2.114') # zurst alles loeschen von Position 1.0 bis 2.114 (Zeile/Spalte)
    textw.insert('1.0','exposure_speed:'+str(camera.exposure_speed)+'|'+'shutter_speed:'+str(camera.shutter_speed)+'|'
    +'fps:'+str(camera.framerate)+'|'+'contrast:'+str(camera.contrast)+'|'+'exposure_compensation:'+str(camera.exposure_compensation)+'|'
    +'brightness:'+str(camera.brightness)+'|'+'awb_gains (red/blue):'+str(camera.awb_gains)+'|'+'saturation:'+str(camera.saturation)+'|'
    +'sharpness:'+str(camera.sharpness)+'|'+'iso:'+str(camera.iso))

def take_picture(picfile): #Grundfunktion zur Einzelbildaufnahme
    camera.stop_preview()
    camera.resolution=(2592,1944)
    camera.exposure_mode='off'
    camera.image_denoise=False
    sleep(1)
    try:
        #camera.capture(picfile,format='jpeg',resize=None,quality=100)
        camera.capture(picfile,format='jpeg',resize=None,bayer=True)
        print "Image",picfile,"successful created and saved!"
        print_values()
    except:
        tkMessageBox.showerror("create file","Error create file: %s" % picfile)

def mk_pic(): # Einzelbildaufnahme mit Flatfieldkorrektur ja/nein
    global flatfieldname
    preview_on()
    tkMessageBox.showinfo("Information","Suchen Sie nun einen geeigenten Ausschnitt fuer die Aufnahme und druecken Sie erst dann OK!")
    preview_off()
    basename=tkFileDialog.asksaveasfilename(initialdir=initialimagedir,initialfile=initialbasename)
    if not basename:
        tkMessageBox.showinfo("Information","'Bild aufnehmen' wird abgebrochen!")
        return
    picfile=basename+'.jpg'
    take_picture(picfile)
    result=tkMessageBox.askquestion("Flatfield","Soll auch eine Flatfieldkorrektur gemacht werden?")
    if result=='yes':
        if flatfieldname!='none':
            print "flatfieldname: ",flatfieldname,"picfile:",picfile
            result=tkMessageBox.askyesno("Flatfield","Flatfield wurde schon erstellt-bestehende Aufnahme verwenden(ja) oder Flatfieldaufnahme neu erstellen(nein)?")
            if result==False:
                flatfile=mk_flat()
            calc_withflat(flatfieldname,picfile)
            tkMessageBox.showinfo("Flatfield","Flatfieldkorrektur wurde gemacht")
        else:
            tkMessageBox.showerror("Kein Flatfield","Keine Flatfieldaufnahme gefunden")
            flatfieldname=mk_flat()
            calc_withflat(flatfieldname,picfile)
    else:
        tkMessageBox.showinfo("picfile","Aufnahme erstellt unter dem Namen: %s" % picfile)

def mk_picchain(): # erstellt eine Serie geleicher Aufnahmen, damit davon ein Durchschnkittswert ermittelt werden kann
    imagelist=[]
    preview_on()
    tkMessageBox.showinfo("Information","Suchen Sie nun einen geeigenten Ausschnitt fuer die Aufnahmen und druecken Sie erst dann OK!")
    preview_off()
    values=set_values()
    print "Active Values for the picamera:",values
    count=tkSimpleDialog.askinteger("Anzahl Aufnahmen","Wieviele Aufnahmen sollen gemacht werden?",initialvalue=6)
    if count==None:
        tkMessageBox.showinfo("Information","'Bildserie erstellen' wird abgebrochen!")
        return
    basename=tkFileDialog.asksaveasfilename(initialdir=initialimagedir,initialfile=initialbasename)
    for number in range(0,count):
        picfile=basename+str(number)+'.jpg'
        take_picture(picfile)
        imagelist.append(picfile)
    print imagelist
    result=tkMessageBox.askyesno("Flatfield","Wollen Sie die Aufnahmen mit (ja) oder ohne (nein) Flatfieldkorrektur?")
    if result==True:   
        if flatfieldname!='none':
            result=tkMessageBox.askyesno("Flatfield","Flatfield wurde schon erstellt - bestehende Aufnahme verwenden(ja) oder Flatfieldaufnahme neu erstellen?")
            if result==False:
                flatfile=mk_flat()
        else:
            flatfile=mk_flat()
        for picfile in imagelist:
            calc_withflat(flatfile,picfile)
    outputfilename=basename+'average.jpg'
    make_average(imagelist,outputfilename)
    
def mk_flat(): #Grundfunktion - erstellt Flatfieldaufnahme
    preview_on()
    tkMessageBox.showinfo("Information","Suchen Sie nun einen geeigenten Ausschnitt fuer das Flatfield und druecken Sie erst dann OK!")
    preview_off()
    values=set_values()
    print "Active Values for the picamera:",values
    #basename=tkFileDialog.asksaveasfilename(initialdir=initialimagedir,initialfile=initialflatname)
    flatpic=initialimagedir+'/'+'flatfileimage.jpg'
    take_picture(flatpic)
    global flatfieldname
    flatfieldname=flatpic
    return flatfieldname

def make_average(filelist,outputfilename): #calculates an average of a series of images
    try:
        w,h=Image.open(filelist[0]).size
        N=len(filelist)
        arr=numpy.zeros((h,w,3),numpy.float)
        for im in filelist:
            imarr=numpy.array(Image.open(im),dtype=numpy.float)
            arr=arr+imarr/N
            print "Patience - average-image is going to be calculated"
        #arr=numpy.array(numpy.round(arr),dtype=numpy.uint8)
        imsave(str(outputfilename),arr)
        print "Averaged image",outputfilename,"saved"
    except:
        tkMessageBox.showerror("create file","Error create file: %s" % outputfilename)

def start_hdr(): # func that ask all the things befor activating the hdr-calculation
    global hdrflatfilenames
    global speeds
    global speedssec
    hdrfilenames=[]
    values=set_values()
    if not speeds:
        speeds,speedssec=def_exposures()
    if (len(speeds)!=amounthdrpics.get()):
	speeds,speedssec=def_exposures()
    if (len(speeds)!=len(hdrflatfilenames)):
	hdrflatfilenames=[]
    print "Active Values for the picamera:",values
    preview_on()
    tkMessageBox.showinfo("Information","Suchen Sie nun einen geeigenten Ausschnitt fuer die HDR-Aufnahmen und druecken Sie erst dann OK!")
    preview_off()
    basename=tkFileDialog.asksaveasfilename(initialdir=initialimagedir,initialfile=initialbasename)
    if basename:
        hdrfilenames=mk_exposures(speeds,basename)
        result=tkMessageBox.askyesno("Flatfield","Wollen Sie die HDR-Aufnahmen mit (ja) oder ohne (nein) Flatfieldkorrektur?")
        if result==True:
            if hdrflatfilenames:
                result=tkMessageBox.askyesno("Flatfield","Sollen bestehende Flatfieldaufnahmen (ja) verwendet werden oder sollen die Aufnahmen neu erstellt werden.")
                if result==False:
                    del hdrflatfilenames[:]
                
            if not hdrflatfilenames:
                print "hdrflatfilenames:",hdrflatfilenames,"IS empty!"
                values=set_values()
                print "Active Values for the picamera:",values
                tkMessageBox.showinfo("Information","Flatfieldaufnahmen muessen erst erstellt werden.")
                preview_on()
                tkMessageBox.showinfo("Information","Suchen Sie einen geeigenten Ausschnitt fuer die Flatfieldaufnahmen und druecken Sie erst dann OK!")
                preview_off()
                flatname=initialimagedir+"/"+initialflatname
                if flatname:
                    hdrflatfilenames=mk_exposures(speeds,flatname)
                else:
                    tkMessageBox.showwarning("Warning","Flatfield-Erstellung vom Benutzer abgebrochen!")
                    print "Warning - flatfield-creation canceld by user!"
                    return
            
            global flatokay
            flatokay=True
        else:
            flatokay=False
        global hdrproductname
        hdrproductname=basename
        print "basename:",basename,"hdrproductname:",hdrproductname
        bake_hdr_thread(flatokay,hdrfilenames,hdrflatfilenames,hdrproductname,speedssec)
    else:
        tkMessageBox.showwarning("Warning","Keine HDR-Aufnahmen erstellt!")#Frage nach Dateiname wurde abgebrochen

def def_exposures(): # erzeugt 5,6 oder 7 Belichtungswerte
    speeds=[]
    speedssec=[]
    hdrpics=amounthdrpics.get()
    center=camera.shutter_speed
    print "Anzahl HDR-Aufnahmen:",hdrpics
    if hdrpics==5:
	denominator=4
    if hdrpics==6:
	denominator=6
    if hdrpics==7:
	denominator=7
    if hdrpics==8:
	denominator=8
    first=center/denominator
    first=first/2
    if denominator==4:
	denominator=5
    for steps in range(0,denominator):
        speeds.append(first)
        speedssec.append(first/1000000.0)
        first=first+first
    print "speeds:", speeds
    print "speedssec", speedssec
    return speeds, speedssec

def mk_exposures(speeds,basename):#erzeugt unterschiedliche belichtete Aufnahmen
    camera.stop_preview()
    camera.exposure_mode='off'
    camera.resolution=(2592,1944)
    camera.image_denoise=False
    camera.iso=100
    filenames=[]
    for speed in speeds: 
        picfile=basename+str(speed)+'.jpg'
        camera.shutter_speed=speed
        fps=1000000/speed
        if fps>30:
            fps=30 
        camera.framerate=fps
        sleep(1)
        try:
            camera.capture(picfile,format='jpeg',resize=None,quality=100)
            filenames.append(picfile)
            print "Erfolg:",picfile," erzeugt"
        except:
            tkMessageBox.showerror("create file","Error create file: %s" % picfile)
    return filenames 

def bake_hdr(flatokay,hdrfilenames,hdrflatfilenames,basename,speedssec): # Erzeugt aus den 5,6 oder 7 unterschiedlich belichteten Aufnahmen eine Tonmapping-Aufnahme
    if flatokay==True:
        for flatfile,picfile in zip(hdrflatfilenames,hdrfilenames):
            calc_withflat(flatfile,picfile)
    img_fn=hdrfilenames
    img_list=[cv2.imread(fn) for fn in img_fn]
    # for Robertson and Debvec:
    #exposure_times=numpy.array(speedssec,dtype=numpy.float32)
    #Debevec:
    #merge_debvec = cv2.createMergeDebevec()
    #hdr_debvec = merge_debvec.process(img_list, times=exposure_times.copy())
    # Robertson:
    #merge_robertson = cv2.createMergeRobertson()
    #hdr_robertson = merge_robertson.process(img_list, times=exposure_times.copy())
    # Mertens:
    merge_mertens = cv2.createMergeMertens()
    res_mertens = merge_mertens.process(img_list)
    # Robertson:
    #tonemap2 = cv2.createTonemapDurand(gamma=1.3)
    #res_robertson = tonemap2.process(hdr_robertson.copy())
    # Debvec:
    #tonemap1 = cv2.createTonemapDurand(gamma=2.2)
    #res_debvec = tonemap1.process(hdr_debvec.copy()) 
    # Convert datatype to 8-bit and save
    res_mertens_8bit = numpy.clip(res_mertens*255, 0, 255).astype('uint8')
    #res_robertson_8bit = numpy.clip(res_robertson*255, 0, 255).astype('uint8')
    #res_debvec_8bit = numpy.clip(res_debvec*255, 0, 255).astype('uint8')
    try:
        cv2.imwrite(basename+"fusion_mertens.jpg", res_mertens_8bit)
        print "Image",basename+"fusion_mertens.jpg successfully saved"
        #cv2.imwrite(basename+"ldr_robertson.jpg", res_robertson_8bit)
        #print "Image",basename+"ldr_robertson.jpg  successfully saved"
        #cv2.imwrite(basename+"ldr_debvec.jpg", res_debvec_8bit)
        #print "Image",basename+"ldr_debvec.jpg  successfully saved"
    except:
        print "Problem - fusion_mertens.jpg could not be saved"

def bake_hdr_thread(flatokay,hdrfilenames,hdrflatfilenames,basename,speedssec):
    global thread1
    thread1=MyThread(1,"bake_hdr_thread",flatokay,hdrfilenames,hdrflatfilenames,basename,speedssec)
    thread1.start()
    print "Thread bake_hdr_thread started"
    
def calc_withflat(flatpic,picfile): # fuehrt die Flatfield-Korrektur aus
    try:
       image_data=imread(picfile).astype(numpy.float32)
       flat_data=imread(flatpic).astype(numpy.float32)
       final_data=image_data/flat_data
       print "Image",picfile,"divided with flatfile",flatpic
       imsave(str(picfile),final_data)
       print "Corrected Image",picfile,"saved!"
    except:
       tkMessageBox.showerror("flatfile","Problem mit Flatfield-Correction: %s/%s" % flatpic % picfile)
       
def set_values(): # set values which will used for taking pictures
    camera.awb_mode='off'
    camera.iso=w9.get()
    camera.awb_gains=(w1.get(),w2.get())
    camera.brightness=w4.get()
    camera.contrast=w5.get()
    camera.exposure_compensation=w6.get()
    camera.saturation=w7.get()
    camera.sharpness=w8.get()
    sspeed=w3.get()
    camera.shutter_speed=sspeed # integer,microseconds, 1000000=eine Sekunde!
#    camera.exposure_speed=sspeed
    if greycolors.get():
    	camera.color_effects=(128,128)
    else:
	camera.color_effects=None
    fps=1000000/sspeed
    if fps>15:
       fps=15
    camera.framerate=fps # wichtig wenn exposure_mode auf off
    values={"iso":camera.iso,"brightness":camera.brightness,"contrast":camera.contrast,"saturation":camera.saturation,"sharpness":camera.sharpness,"shutter_speed":sspeed,"framerate":camera.framerate}
    print_values()
    print values
    return values

def set_default(): # set camera-values back to default values, as defined when programm is started
    w1.set(1.5)    # awb red 
    w2.set(1.2)    # awb blue
    w3.set(90000)  # shutter speed
    w4.set(50)     # brightness
    w5.set(0)      # contrast
    w6.set(0)      # exposure_compensation
    w7.set(0)      # saturation
    w8.set(0)      # sharpness
    w9.set(100)    # camera.iso
    amounthdrpics.set(5)
    camera.color_effects=None
    camera.rotation=0
    set_values()

def preview_on():
    camera.exposure_mode='auto'
    camera.resolution=(1280,960)
    #camera.preview.alpha=200
    camera.start_preview()
    camera.preview.fullscreen=False
    #camera.preview.window=(100,100,640,480)
    camera.preview.window=(0,0,1280,960)
    global preview
    preview=True

def preview_off():
    camera.stop_preview()
    global preview
    preview=False

def quit_prog():
    master.destroy()
    camera.stop_preview()
    GPIO.cleanup()
    camera.close()


camera = picamera.PiCamera()
master=Tk()
#master.geometry('+640+100')
master.geometry('+1240+5')

greycolors=BooleanVar()
amounthdrpics=IntVar()

textw=Text(master,height=3,width=82)
textw.pack()

previewframe=Frame(master)
#picframe=Frame(master)
mkpicframe=Frame(master,relief='ridge',border=5)
anwendframe=Frame(master,relief='sunken',border=1)
closeframe=Frame(master,relief='sunken',border=1)

closeframe.pack(side=BOTTOM,fill='x')
mkpicframe.pack(side=BOTTOM)
previewframe.pack(side=BOTTOM)
anwendframe.pack(side=BOTTOM)

w1=Scale(master,from_=0,to=8,resolution=0.1,length=580,orient=HORIZONTAL,border=0,label='awb red')
w1.set(1.0)
w1.pack()
w2=Scale(master,from_=0,to=8,resolution=0.1,length=580,orient=HORIZONTAL,border=0,label='awb blue')
w2.set(1.0)
w2.pack()
w3=Scale(master,from_=5000,to=1000000,resolution=5000,length=580,orient=HORIZONTAL,border=0,label='shutter speed')
w3.set(30000)
w3.pack()
w4=Scale(master,from_=0,to=100,length=580,orient=HORIZONTAL,border=0,label='brightness')
w4.set(50)
w4.pack()
w5=Scale(master,from_=-100,to=100,length=580,orient=HORIZONTAL,border=0,label='contrast')
w5.set(0)
w5.pack()
w6=Scale(master,from_=-25,to=25,length=580,orient=HORIZONTAL,border=0,label='exposure_compensation')
w6.set(0)
w6.pack()
w7=Scale(master,from_=-100,to=100,length=580,orient=HORIZONTAL,border=0,label='saturation')
w7.set(0)
w7.pack()
w8=Scale(master,from_=-100,to=100,length=580,orient=HORIZONTAL,border=0,label='sharpness')
w8.set(0)
w8.pack()
w9=Scale(master,from_=100,to=800,resolution=100,length=580,orient=HORIZONTAL,border=0,label='iso')
w9.set(0)
w9.pack()

Button(anwendframe,text='Anwenden',command=set_values).pack(side=LEFT,pady=10,padx=10)
Button(anwendframe,text='Alle Werte auf default',command=set_default).pack(side=RIGHT,padx=10,pady=10)
Button(previewframe,text='Vorschau starten',command=preview_on).pack(side=LEFT,pady=10)
Button(previewframe,text='Vorschau beenden',command=preview_off).pack(side=LEFT,pady=10,padx=100)

Label(mkpicframe,text="Anzahl Aufnahmen fuer HDRs:",fg="black",font="Times").grid(row=1,column=0)
Radiobutton(mkpicframe,text="5",variable=amounthdrpics,value=5).grid(row=1,column=1)
Radiobutton(mkpicframe,text="6",variable=amounthdrpics,value=6).grid(row=1,column=2)
Radiobutton(mkpicframe,text="7",variable=amounthdrpics,value=7).grid(row=1,column=3)
Radiobutton(mkpicframe,text="8",variable=amounthdrpics,value=8).grid(row=1,column=4)
Button(mkpicframe,text='HDR.Bildfolge erzeugen',command=start_hdr).grid(row=1,column=5)
Checkbutton(mkpicframe,text="Aufnahme in Graustufen",variable=greycolors).grid(row=2,column=0)
Button(mkpicframe,text='Bild aufnehmen',command=mk_pic).grid(row=3,column=0)
Button(mkpicframe,text='Flatfield erstellen',command=mk_flat).grid(row=4,column=0)
Button(mkpicframe,text='Durchschnittsbild aus Serie',command=mk_picchain).grid(row=3,column=5)

#Button(previewframe,text='Bild anzeigen',command=show_picture).pack(side=RIGHT,pady=10)
Button(closeframe,text='Programm beenden',command=quit_prog).pack(side=RIGHT,expand=1)

set_default()
set_values()
master.protocol("WM_DELETE_WINDOW",quit_prog)

mainloop()

GPIO.cleanup()
camera.close()

