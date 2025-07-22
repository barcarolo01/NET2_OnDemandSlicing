#!/usr/bin/env python3

import tkinter as tk
import requests
from PIL import Image, ImageTk
import subprocess

# IP and port of the REST API controller
IP_controller='localhost'
port_controller='8080'

# Path for GUI images
images_path="Images/"
base_image_path = images_path+"white.png"
Slices = {}

is_s2_s4_down = False   # State of the s2-s4 link (The only with "fault tolerance")
assistance_images=set()
global_assistance_image = None
assistance_devices=""

# This method fetches the set of slices and their current state from the controller (ryu_controller.py)
def fetch_slices():
    response = requests.get('http://localhost:8080/slice/get_slices')
    if response.status_code == 200:
        Slices = response.json()
        print("Slices fetched successfully")
        return Slices
    else:
        print(f"[!] Unable to contact ryu_controller at {IP_controller}:{port_controller}")
        exit()
    
# Function to load and resize image
def load_image(path, size):
    image = Image.open(path)
    image = image.resize(size, Image.ANTIALIAS)
    return ImageTk.PhotoImage(image)

# Toggle buttons
def toggle(label, name):
    global Slices
    
    if name == "Assistance":     # Assistance slice behaves differently: it is managed in another method
            Assistance(label)
    else:
        if Slices[name]: #Button state before the click
            img = load_image(images_path+"off.png", (50, 25))
            command = "remove"
        else:
            img = load_image(images_path+"on.png", (50, 25))
            command = "add"

        response=requests.post(f'http://{IP_controller}:{port_controller}/slice/{command}_{name}')
        
        if response.status_code == 200:
            Slices[name] = not Slices[name] # Change the state of the button
            label.configure(image=img)
            label.image = img  # Do not remove (Garbage collection)
            # Update and shown the topology image
            topology_img=show_topology()
            canvas.topology_img = topology_img  # Update reference
            canvas.itemconfig(canvas_image, image=topology_img)
            body_bytes = response.content
            body = body_bytes.decode('utf-8')
            print(body)
        else:
            print(f'WARNING! Returned status code: {response.status_code}')
    
# This method dynamically create the image to be shown with the activated slices highlighted
def show_topology():
    global is_s2_s4_down
    global base_image_path 
    global global_assistance_image
    base_image = Image.open(base_image_path).convert("RGBA")
    base_image = base_image.resize((1280,720), Image.ANTIALIAS)

    for name,status in Slices.items():
        if status and name != "Assistance": # If the slice is active, show the appropriate highlighting
            if name == "Telesurgery" and is_s2_s4_down: 
                overlay = Image.open(images_path+name+"_slice_backup.png").convert("RGBA")
            else:
                overlay = Image.open(images_path+name+"_slice.png").convert("RGBA")
            
            
            overlay=overlay.resize((1280,720),Image.ANTIALIAS)
            base_image = Image.alpha_composite(base_image, overlay)
        
    # The visualization of the Assistance slice is managed outside of the for-loop
    if global_assistance_image:
        base_image = Image.alpha_composite(base_image, global_assistance_image)

    # Top layer: topology
    if is_s2_s4_down: # If s2-s4 link id down, show it in the topology image
        overlay = Image.open(images_path+"topology_broken_IP_transparent.png").convert("RGBA")
    else:
        overlay = Image.open(images_path+"topology_IP_transparent.png").convert("RGBA")
    
    overlay=overlay.resize((1280,720),Image.ANTIALIAS)
    base_image = Image.alpha_composite(base_image, overlay)
    topology_img = ImageTk.PhotoImage(base_image) 
    return topology_img

# This method simulate a failure / repair in the link between s2-eth5 <--> s4-eth3
def breaklink():
    global image_label
    global is_s2_s4_down
    is_s2_s4_down = not is_s2_s4_down

    if is_s2_s4_down: #Update value of "is_s2_s4_down"
        btn_break.set("Restore s2-s4 Link")
        subprocess.run(["sudo","ovs-ofctl","-O OpenFlow13", "mod-port", "s2", "s2-eth5", "down"])
        print("Link s2 <-> s4 DOWN")

    else:
        btn_break.set("Break s2-s4 link")
        subprocess.run(["sudo","ovs-ofctl","-O OpenFlow13", "mod-port", "s2", "s2-eth5", "up"])
        print("Link s2 <-> s4 UP")
    
    #Update the topology image
    topology_img=show_topology()
    canvas.topology_img = topology_img  # update reference
    canvas.itemconfig(canvas_image, image=topology_img)

# This method fetches the checkboxes status and:
#   1) Composes the appropriate image for the assistance slice
#   2) Perform the request for assistance slice activation to the ryu controller
def Assistance(button_label):
    global image_label
    global assistance_images
    global global_assistance_image
    devices=set()
    
    Slices['Assistance'] = not Slices['Assistance']
    # Checkbox are disabled while the slice is activated
    for cb in checkbox_widgets.values():
        if Slices['Assistance']:
            cb.configure(state="disabled")
        else:
            cb.configure(state="active")  

    # Images to me merged and devices to be serviced are respectively collected into 'assistance_images' and 'devices'
    if Slices['Assistance']: #New value
        devices.clear()
        assistance_images.clear()

        #Office A
        if checkbox_vars["cb_h6"].get() or checkbox_vars["cb_h7"].get():
            assistance_images.add("s2_s3.png")
        if checkbox_vars["cb_h6"].get():
            assistance_images.add("s2_s5.png")
            assistance_images.add("s3_h6.png")
            devices.add("h6")
        if checkbox_vars["cb_h7"].get():
            assistance_images.add("s2_s5.png")
            assistance_images.add("s3_h7.png")
            devices.add("h7")

        #IoT
        if checkbox_vars["cb_h3"].get() or checkbox_vars["cb_h4"].get() or checkbox_vars["cb_h5"].get():
            assistance_images.add("s2_s5.png")
        if checkbox_vars["cb_h3"].get():
            assistance_images.add("s2_h3.png")
            devices.add("h3")
        if checkbox_vars["cb_h4"].get():
            assistance_images.add("s2_h4.png")
            devices.add("h4")
        if checkbox_vars["cb_h5"].get():
            assistance_images.add("s2_h5.png")
            devices.add("h5")

        #LAB
        if checkbox_vars["cb_h8"].get():
            assistance_images.add("s5_h8.png")
            devices.add("h8")

        #Datacenter and patients
        if checkbox_vars["cb_datacenter"].get() or checkbox_vars["cb_patient"].get(): 
            assistance_images.add("s4_s5.png")
        if checkbox_vars["cb_datacenter"].get() :
            assistance_images.add("s4_h10.png")
            devices.add("h10")
        if checkbox_vars["cb_patient"].get():
            assistance_images.add("s4_h12.png")
            devices.add("h12")


        base_image = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))  # Transparent base
        for img_name in assistance_images:
            overlay = Image.open(images_path+"Remote_Assistance_Slice/"+img_name).convert("RGBA")
            overlay=overlay.resize((1280,720),Image.ANTIALIAS)
            base_image = Image.alpha_composite(base_image, overlay)
            
        global_assistance_image = base_image
    
    else: # If the remote assistance must be disabled
        global_assistance_image = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))  # Transparent base

    # Formatting a string with the names of selected devices separated by a '-'
    strDevices=""
    for dev in devices:
        strDevices+=dev+"-"
    strDevices=strDevices[:-1]

    if Slices['Assistance']:
        response=requests.post(f'http://{IP_controller}:{port_controller}/slice/add_Assistance',data=strDevices)
        img = load_image(images_path+"on.png", (50, 25))
    else:
        response=requests.post(f'http://{IP_controller}:{port_controller}/slice/remove_Assistance')
        img = load_image(images_path+"off.png", (50, 25))
    
    if response.status_code == 200:
        button_label.configure(image=img)
        button_label.image = img  # Do not remove (Garbage collection)
        topology_img=show_topology()
        canvas.topology_img = topology_img  # Update reference
        canvas.itemconfig(canvas_image, image=topology_img)
    
    
# ======================================== GUI ========================================
if __name__ == "__main__":
    # Main window setup
    Slices = fetch_slices()

    window = tk.Tk()
    window.title("Network slicing GUI")
    window.geometry("1500x740")
    window.resizable(False,False)

    #Frame initialization
    left_frame = tk.Frame(window, width=1280, height=740)
    left_frame.pack(side="left", fill="both")
    topology_img = show_topology()

    canvas = tk.Canvas(left_frame, width=1280, height=720)
    canvas.pack()
    canvas_image = canvas.create_image(0, 0, anchor="nw", image=topology_img)

    # Store references globally (important to avoid garbage collection)
    canvas.topology_img = topology_img

    # Checkbox tuples: names, x_position, y_position
    checkbox_data = [
        ("cb_h3", 50, 520),
        ("cb_h4", 50,670),
        ("cb_h5", 30,350),
        ("cb_h6", 160,70),
        ("cb_h7", 160,180),
        ("cb_h8", 930,350),
        ("cb_datacenter", 670,650),
        ("cb_patient", 505,650)
    ]
    checkbox_vars = {}
    checkbox_widgets = {}

    for item in checkbox_data:
        name = item[0]
        x = item[1]
        y = item[2]
        var = tk.IntVar()
        cb = tk.Checkbutton(left_frame, variable=var)
        canvas.create_window(x, y, window=cb)
        checkbox_vars[name] = var
        checkbox_widgets[name] = cb


    # ========== RIGHT SIDE ==========
    right_frame = tk.Frame(window, width=220, height=70, bg="#f0f0f0")
    right_frame.pack(side="right", fill="both")

    horizontal_row = tk.Frame(right_frame, bg="#f0f0f0")
    horizontal_row.pack(pady=(20, 10))

    # ON/OFF toggle button images
    toggle_on_img = load_image(images_path+"on.png", (50, 25))
    toggle_off_img = load_image(images_path+"off.png", (50, 25))

    toggle_widgets = []
    #Creation of the buttons on the right
    for name, status in Slices.items():
        row = tk.Frame(right_frame, bg="#f0f0f0")
        row.pack(pady=(22, 10))

        lbl = tk.Label(row, text=name, bg="#f0f0f0", font=("Arial", 10), anchor="w", width=15)
        lbl.pack(side="left", padx=(10, 5), anchor="w")
        if Slices[name]:
            toggle_label = tk.Label(row, image=toggle_on_img, bg="#f0f0f0", cursor="hand2")
        else:
            toggle_label = tk.Label(row, image=toggle_off_img, bg="#f0f0f0", cursor="hand2")
        toggle_label.pack(side="left",padx=(22,20))

        if name == "Assistance":
            toggle_label.bind("<Button-1>", lambda e, l=toggle_label:Assistance(l))
        else:
            toggle_label.bind("<Button-1>", lambda e, l=toggle_label, n=name: toggle(l, n))

        toggle_widgets.append(toggle_label)

    # Button to change s2-s4 link status
    btn_break=tk.StringVar()
    btn_break.set("Break s2-s4 link")
    break_s2_s4_button = tk.Button(right_frame, textvariable=btn_break, font=("Arial", 10), width=17, height=3, command=breaklink)
    break_s2_s4_button.pack(pady=(40, 10))

    # Footer
    footer = tk.Label(left_frame, text="Networking II project - Nicola Barcarolo", anchor="e")
    footer.pack(fill="x")

    window.mainloop()