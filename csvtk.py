import tkinter as tk
import sys
from sys import path
import numpy as np
from time import time as systime
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from glob import glob
import os
from multiprocessing import Pool
import sounddevice as sd

from argparse import ArgumentParser, SUPPRESS
from argparse import RawTextHelpFormatter
import tkfilebrowser

from inc.proc_bg import Update_Queue_Clearer, Update_Queue_Reader, compute_spectrogram, A

def parse_files(dirs):
    files = []
    for d in dirs:
        G = glob(os.path.join(d,"**/*.wav"), recursive=True)
        files += [ G ]

    files_ = []
    for F in files:
        files_ += F

    global FILES_LIST
    FILES_LIST = sorted(files_)

def do_griflim(*ac):
    # threaded: compute griffin lim restoration of complex spectrogram and place into waveform
    from librosa import griffinlim as GriffinLim
    dat = ac[0]
    minlevel = 1e-5
    grif = GriffinLim(np.maximum(np.power(10,dat) - 10 - minlevel, 0)/1000,
                      n_iter=32,
                      hop_length=250,
                      init=None)
    return grif

def play_the_sound(*ac):
    # play the sound computed by griffin lim
    sd.stop()
    sd.play(ac[0][0].astype(np.float32) * 1000, 16000)

def close_playback_threads():
    for p in PLAYBACK_THREADPOOL:
        q = PLAYBACK_THREADPOOL.pop()
        q.close()

class App(tk.Frame):
    def __init__(self, root, **av):
        super().__init__(root)
        #####################
        # Configure GUI
        self.root = root
        root.geometry("500x500")
        root.title("f(X) <-- X")
        self.pack()
        self.construct_spectrogram_plot()

        # file browser/selection frame
        br_ = tk.Toplevel(root)
        self.br = self.Selector_Frame(br_, self)
        self.br.list_box.select_set(0)
        self.br.list_box.bind("<<ListboxSelect>>", adjustment_event_toplay)

        # parameter adjustment frame
        adj_ = tk.Toplevel(root)
        adj = self.Param_Adjustments_Frame(
            adj_,
            self,
            action=adjustment_event,
            param_limits=av['param_limits']
        )
        for scale in adj.scales:
            scale.bind("<ButtonRelease-1>", adjustment_event_toplay)

        # energy histograms/density frame
        hist_ = tk.Toplevel(root)
        self.hist = self.Energies_Frame(hist_, self)

        #################
        # Configure background threads
        self.uqm = Update_Queue_Reader(self, USER_INTERACT_QUEUE,
                                        refresh_rate=av['refresh_rate'])
        self.uqc = Update_Queue_Clearer()
        self.uqm.start()
        self.uqc.start()

    def destroy(self):
        close_playback_threads()

        super().destroy()

    def construct_spectrogram_plot(self):
        fig = Figure(figsize = (18,12),
                    dpi = 100)

        self.plot1 = fig.add_subplot(121)
        self.plot2 = fig.add_subplot(122)
        self.canvas = FigureCanvasTkAgg(fig,
                                        master = self)
        self.canvas.draw()

        self.canvas.get_tk_widget().pack(anchor=tk.E, side=tk.LEFT)
    def update_refresh_interactive(self, event=None):
        # GUI interaction events that are not time-limited
        # (ie. button clicks but not slider drags) get passed through here
        # this method calls other methods to handle computation and plotting

        adjustment_event()
        self.refresh_interactive()

    def refresh_interactive(self, event=None, play=True):
        # all plot and sound playback events are passed through here
        playback_thread = Pool(1)
        close_playback_threads()
        global u_, v_, s_, t_

        u, params, play, _ = USER_INTERACT_QUEUE[-1]

        USER_INTERACT_QUEUE.append((u, params, False, _))

        X, Y = compute_spectrogram(u, params)
        self.plot(X, Y)
        togrif= Y @ A[1]

        if play:
            playback_thread.starmap_async(do_griflim,
                                          [[togrif.T,],],
                                          callback=play_the_sound)
            PLAYBACK_THREADPOOL.append(playback_thread)

    def plot(self, X, Y):
        # update the primary spectrogram canvas on request
        # from refresh_interactive method
        self.plot1.clear()
        self.plot1.pcolormesh(Y)
        self.plot2.clear()
        self.plot2.pcolormesh(X)

        self.hist.plot1.clear()
        self.hist.plot2.clear()
        bins,_ = np.histogram(Y.ravel(), density=True, bins=25)
        bins = bins / len(bins)
        self.hist.plot1.bar(
            np.linspace(Y.min(), Y.max(), len(bins)),
            bins,
            width = (Y.max() - Y.min())/ len(bins))
        self.hist.plot2.bar(
            np.linspace(Y.min(), Y.max(), len(bins))[1:],
            bins[1:],
            width = (Y.max() - Y.min())/ len(bins))

        self.canvas.draw()
        self.hist.canvas.draw()

    class Energies_Frame(tk.Frame):

        def __init__(self, root, app):
            super().__init__(root)
            root.geometry("500x500")
            root.title("Energy Densities")
            self.pack()
            self.construct_energy_plot()
            root.protocol("WM_DELETE_WINDOW", app.root.destroy)

        def construct_energy_plot(self):
            fig = Figure(figsize = (18,12), dpi = 100)

            self.plot1 = fig.add_subplot(211, sharex=None)
            self.plot2 = fig.add_subplot(212, sharex=None)
            self.canvas = FigureCanvasTkAgg(fig,
                                            master = self)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(anchor=tk.E, side=tk.LEFT)

    class Selector_Frame(tk.Frame):
        def __init__(self, root, app):
            super().__init__(root)

            root.geometry("200x300")
            root.title("")
            self.pack()
            list_box = tk.Listbox(root, selectmode="browse")

            self.list_box = list_box
            list_box.pack(side='left', fill='both', expand=True)

            scrollbar = tk.Scrollbar(root)
            scrollbar.pack(side = tk.RIGHT, fill = tk.BOTH)
            list_box.config(yscrollcommand = scrollbar.set)
            scrollbar.config(command = list_box.yview)

            root.protocol("WM_DELETE_WINDOW", app.root.destroy)

            menubar = tk.Menu(root)
            filemenu = tk.Menu(menubar, tearoff=0)
            filemenu.add_command(label="Open", command=ask_files)
            filemenu.add_separator()
            filemenu.add_command(label="Exit", command=app.root.destroy)
            menubar.add_cascade(label="File", menu=filemenu)

            root.config(menu = menubar)

    def load_files(self):
        # load the files into file list
        self.br.list_box.delete('0', 'end')

        for f in FILES_LIST:
            self.br.list_box.insert(tk.END, os.path.split(f)[-1])


    class Param_Adjustments_Frame(tk.Frame):
        def __init__(self, root, app, action=None, param_limits=None):
            assert not param_limits is None
            super().__init__(root)
            root.geometry("400x250")
            root.title("Parameters")
            self.pack(fill="both", expand=True)

            root.protocol("WM_DELETE_WINDOW", app.root.destroy)

            self.scales = []

            global u_, v_, s_, t_
            u_, v_, s_, t_ = tk.DoubleVar(), tk.DoubleVar(), tk.DoubleVar(), tk.DoubleVar()

            global SOUND_ON
            SOUND_ON = tk.BooleanVar()

            i = 0
            for param_settings in [(u_, param_limits['u0'],
                       param_limits['uoo'], param_limits['u0'] ),\
                      (v_, param_limits['v0'],
                       param_limits['voo'], param_limits['voo']  ),\
                      (s_, param_limits['s0'],
                       param_limits['soo'], param_limits['soo']),\
                      (t_, param_limits['t0'],
                       param_limits['too'], param_limits['too'])]:

                # unpack parameter getter object,  lower limit, upper limit, default setting
                u, a, b, mu = param_settings

                param_slider = tk.Scale(self, var=u, orient='vertical', from_=a, to_=b,
                              resolution=float(np.abs(a-b) / 2500), command=action)
                param_slider.set(mu)
                param_slider.grid(row=1, column=i, sticky = "NSEW", pady=5)

                self.scales.append(param_slider)
                i+=1

            i = 0
            for txt in ['u', 'v', 's', 't']:
                la = tk.Label(self, text=txt, font=(TKDEFFONT, 14))
                la.grid(row=0, column=i, sticky= "NSEW", pady=5)
                i+=1

            chk1 = tk.Checkbutton(
                self, text='sound on',variable=SOUND_ON, onvalue=True, offvalue=False)
            chk1.grid(row=1, column=4, sticky="NSEW", pady=1)

            b1 = tk.Button(
                self, text="Play", command=adjustment_event_toplay)

            b1.grid(row=0, column=4, sticky="NSEW", pady=5)

            label = tk.Label(self, text=\
                             "f(X) = ( |X - 100u| + v ) / v + s --> [0,t]")
            label.grid(row=2, column=0, columnspan=5, sticky="NSEW", pady=20)

            self.grid_rowconfigure(0,weight=10)
            self.grid_rowconfigure(1,weight=10)
            self.grid_rowconfigure(2,weight=1)
            self.grid_columnconfigure((0,1,2,3,4),weight=1)

def adjustment_event_toplay(event=None):
    adjustment_event(play=SOUND_ON.get())

def adjustment_event(event=None, play=False):
    fi = FILES_LIST  [GUI_APP.br.list_box.curselection()[-1]]
    USER_INTERACT_QUEUE.append(
        (fi, tuple([ u.get() for u in [u_, v_, s_, t_] ]), play, systime())
    )

def ask_files():
    rootdir = tkfilebrowser.askopendirnames()

    if len(rootdir) > 0:
        parse_files(rootdir)
        GUI_APP.load_files()

class DevNull:
    def write(self, msg):
        pass

def main(args):
    global USER_INTERACT_QUEUE, PLAYBACK_THREADPOOL
    PLAYBACK_THREADPOOL = []
    USER_INTERACT_QUEUE = []

    sys.stderr = DevNull()
    rootdir = args.rootdir
    #prepare customized range of parameters from arg parser
    u0,uoo = [float(j) for j in args.limits_u.split(',')]
    v0,voo = [float(j) for j in args.limits_v.split(',')]
    s0,soo = [float(j) for j in args.limits_s.split(',')]
    t0,too = [float(j) for j in args.limits_t.split(',')]

    param_limits = \
        { 'u0': u0, 'uoo': uoo,
          'v0': v0, 'voo': voo,
          's0': s0, 'soo': soo,
          't0': t0, 'too': too
    }

    global TKDEFFONT
    root = tk.Tk()
    TKDEFFONT = tk.font.nametofont("TkDefaultFont")

    global GUI_APP
    GUI_APP = App(root,
              param_limits=param_limits,
              refresh_rate=args.refresh)

    if rootdir is None:
        ask_files()
    else:
        parse_files(rootdir)
        GUI_APP.load_files()

    GUI_APP.mainloop()

if __name__ == "__main__":
    parser = ArgumentParser(
        prog = "csvtk",
        description = """
Compressive Spectrogram Visualization Toolkit v.0.0

Visualize contractive compression, noise cleaning, and clipping of mel-reduced spectrograms loaded from .wav files.  Useful for manual qualitative correction of noise and blurring due to mel down-projections.  Default parameters are permissible for sound normalized to -18dB.

Currently performs 80-dimensional mel reduction of entire .wav files inside a user-specified root directory, and accepts only 16kHz .wav files.
        """,
        formatter_class=RawTextHelpFormatter)
    parser.add_argument(
        "--fps", dest="refresh", default=12,
        help="number of plot refresh cycles per second / GUI responsiveness.  default 12")

    parser.add_argument(
        "-u", dest="limits_u", default="0,5", help="default 0,5")
    parser.add_argument(
        "-v", dest="limits_v", default="1,100", help="default 1,100")
    parser.add_argument(
        "-s", dest="limits_s", default="-2,0", help="default -2,0")
    parser.add_argument(
        "-t", dest="limits_t", default="0,3",
        help="""default 0,3

u, v, s, t are parameters of the compression and clipping function.
Use -u/v/s/t to configure the range of permissible values in the GUI.

Example: to limit parameters u and v to the [0,10] range, apply
   -u 0,10 -v 0,10

If X is the log spectrogram of a sound, then we display approximately the following function of X:
f(X) = eps + ( |X - 100u| + v ) / v + s, clipped within the interval [0,t]
where eps is the silence floor of around log(10^-5).  Anything below eps is muted prior to application of the function f.
All values between zero and eps are muted following application of the function f.
""")

    # throwaway -f for running inside jupyter repl kernel
    parser.add_argument(
        "-f", dest="jupyter_mode", default="False", help=SUPPRESS
    )

    parser.add_argument(
        dest="rootdir",
        default=None,
        nargs='?',
        help="Recursively load the sound files inside this directory"
    )
    args = parser.parse_args()

    sys.exit(main(args))
