"""Draw the manuscript schematics directly as font-embedded vector PDFs.

Run: python figures/draw_schematics.py --output figures
Requires Python 3.9+ and Matplotlib. No TeX engine or network is used.
The diagrams express the defined model; they are not measurement plots.
"""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, FancyArrowPatch

plt.rcParams.update({'font.family':'STIXGeneral', 'mathtext.fontset':'stix',
                     'font.size':9, 'pdf.fonttype':42, 'ps.fonttype':42,
                     'text.usetex':False, 'axes.unicode_minus':False})
CM = 1 / 2.54

class Drawing:
    def __init__(self, bounds):
        x0,y0,x1,y1 = bounds
        self.fig = plt.figure(figsize=((x1-x0)*CM,(y1-y0)*CM))
        self.ax = self.fig.add_axes([0,0,1,1], xlim=(x0,x1), ylim=(y0,y1))
        self.ax.set_aspect('equal'); self.ax.axis('off')
        self.nodes = {}
        self.labels = []

    def text(self,x,y,label,size=9,ha='center',va='center'):
        artist=self.ax.text(x,y,label,fontsize=size,ha=ha,va=va,
                            linespacing=1.15,clip_on=False,zorder=4)
        self.labels.append([artist,None])
        return artist

    def box(self,name,x,y,w,h,label,dashed=False,shape='rect',size=9):
        style = {'edgecolor':'black','facecolor':'white','linewidth':.55,
                 'linestyle':(0,(4,3)) if dashed else 'solid', 'zorder':2}
        if shape == 'diamond':
            obj = Polygon([(x-w/2,y),(x,y+h/2),(x+w/2,y),(x,y-h/2)],**style)
        elif shape == 'circle': obj = Circle((x,y),w/2,**style)
        else: obj = Rectangle((x-w/2,y-h/2),w,h,**style)
        self.ax.add_patch(obj); self.text(x,y,label,size)
        self.labels[-1][1]=(x-w/2,y-h/2,x+w/2,y+h/2)
        self.nodes[name] = (x,y,w,h,shape)

    def point(self,name,side):
        x,y,w,h,_ = self.nodes[name]
        return {'n':(x,y+h/2),'s':(x,y-h/2),'e':(x+w/2,y),
                'w':(x-w/2,y),'nw':(x-w/2,y+h/2),
                'ne':(x+w/2,y+h/2),'c':(x,y)}[side]

    def line(self,points,dashed=False):
        xs,ys=zip(*points)
        self.ax.plot(xs,ys,color='black',linewidth=.55,
                     linestyle=(0,(4,3)) if dashed else 'solid',zorder=1)

    def arrow(self,p,q,dashed=False,via=()):
        points=[p,*via,q]
        if via:self.line(points[:-1],dashed)
        self.ax.add_patch(FancyArrowPatch(points[-2],points[-1],
                         arrowstyle='-|>',mutation_scale=7.5,linewidth=.55,
                         color='black',shrinkA=0,shrinkB=0,
                         linestyle=(0,(4,3)) if dashed else 'solid',zorder=1))

    def edge(self,a,b,sa='s',sb='n',**kwargs):
        self.arrow(self.point(a,sa),self.point(b,sb),**kwargs)

    def frame(self,x,y,w,h):
        self.ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor='black',
                                   linewidth=.55,linestyle=(0,(4,3)),zorder=0))

    def save(self,out,name):
        # Fixed physical canvas: do not enlarge or rasterize the scientific figure.
        self.fig.canvas.draw()
        renderer=self.fig.canvas.get_renderer()
        x0,x1=self.ax.get_xlim();y0,y1=self.ax.get_ylim()
        for artist,node in self.labels:
            b=artist.get_window_extent(renderer).transformed(self.ax.transData.inverted())
            if b.x0<x0-.02 or b.x1>x1+.02 or b.y0<y0-.02 or b.y1>y1+.02:
                raise ValueError(name+': clipped label '+repr(artist.get_text()))
            if node and (b.x0<node[0]-.02 or b.x1>node[2]+.02 or b.y0<node[1]-.02 or b.y1>node[3]+.02):
                raise ValueError(name+': label exceeds node '+repr(artist.get_text()))
        self.fig.savefig(out/(name+'.pdf'),format='pdf',
                         metadata={'Creator':'Python Matplotlib','Producer':None,
                                   'CreationDate':None,'ModDate':None})
        plt.close(self.fig)

def draw(out):
    d=Drawing((-2.7,-11.0,10.4,2.0))
    def box(name,x,y,label,kind='plain',h=1.35):
        d.box(name,x,y,3.05,h,label,dashed=kind=='bridge',size=8.5)
        patch=d.ax.patches[-1]
        if kind=='data':patch.set_facecolor('#f3f3f3')
        if kind=='check':patch.set_linewidth(.8)
    box('java',0,0,'accepted Java\nsource fragment','data')
    box('front',3.8,0,'fail-closed\nsource bridge','bridge')
    box('src',7.6,0,'bounded source $P$\nand target table $C$','data')
    box('prod',7.6,-2.5,'untrusted certificate\nproducer')
    box('cert',3.8,-2.5,'shared ordered\nMTBDD values\nand outcomes','data')
    box('check',0,-2.5,'independent certificate\nchecker: schema, DAG,\nall assignments','check')
    box('sum',0,-5,'accepted profiles\nmay and robust sets','data')
    box('lower',7.6,-5,'untrusted\ndirect lowerer')
    box('dispatch',7.6,-7.6,'Boolean\ndispatch DAG\nfour action kinds','data')
    box('replay',3.8,-7.6,'independent replay\nchecker: complete\nfinite trace','check')
    box('wprod',0,-7.6,'witness producer\ncoordinate deletion')
    box('wcheck',0,-10.2,'witness checker\nretention\nand necessity','check')
    box('out',3.8,-10.2,'checked omission\nevidence\nsubset-minimal slice','data')
    d.edge('java','front','e','w');d.edge('front','src','e','w')
    d.edge('src','prod');d.edge('prod','cert','w','e');d.edge('cert','check','w','e')
    d.arrow(d.point('src','n'),d.point('check','w'),via=[(7.6,1.55),(-2,1.55),(-2,-2.5)])
    d.text(3.8,1.8,'source binding',size=8.5)
    d.edge('check','sum')
    d.arrow(d.point('src','e'),d.point('lower','e'),via=[(9.7,0),(9.7,-5)])
    d.arrow(d.point('cert','s'),d.point('lower','n'),via=[(3.8,-3.8),(7.6,-3.8)])
    d.edge('lower','dispatch');d.edge('dispatch','replay','w','e')
    d.arrow(d.point('src','ne'),d.point('replay','s'),via=[(9.125,1.1),(-2.4,1.1),(-2.4,-8.8),(3.8,-8.8)])
    d.edge('sum','wprod');d.edge('wprod','wcheck')
    d.arrow(d.point('sum','w'),d.point('wcheck','w'),via=[(-1.8,-5),(-1.8,-10.2)])
    d.edge('wcheck','out','e','w');d.save(out,'certificate-pipeline')

    d=Drawing((-.75,-8.5,9.3,1.25))
    def table(y,truth):
        for i,(bits,val) in enumerate([('$h_0h_1$','$t\\in T(h)$'),('00',truth[0]),('01',truth[1]),('10',truth[2]),('11',truth[3])]):
            for c,label in enumerate((bits,val)):
                d.box('cell'+str(y)+str(i)+str(c),c*1.2,y-i*.7,1.2,.7,label,size=8.5)
                if i:d.ax.patches[-1].set_facecolor('#e0ecfa' if val=='yes' else '#ededed')
    d.text(-.6,.8,'(a) necessity for $S=\\{0,1\\}$',size=9,ha='left')
    table(0,['yes','no','no','yes'])
    d.text(2.6,-1.4,'Base $00$ retains $t$ when both\ncoordinates are fixed.\nRemoving $h_0$ admits $10$;\nremoving $h_1$ admits $01$.',size=8.5,ha='left')
    d.text(-.6,-4.2,'(b) no unique least slice',size=9,ha='left')
    table(-5,['yes','yes','yes','no'])
    d.text(2.6,-6.4,'At base $00$, either $\\{h_0\\}$ or\n$\\{h_1\\}$ suffices. They are incomparable;\ntheir intersection $\\varnothing$ does not suffice.',size=8.5,ha='left')
    d.save(out,'witness-geometry')

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path(__file__).resolve().parent)
    output=parser.parse_args().output
    output.mkdir(parents=True,exist_ok=True)
    draw(output)
