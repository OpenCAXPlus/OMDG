from fealpy.decorator import cartesian, barycentric
from fealpy.mesh import MeshFactory as MF
from fealpy.functionspace import LagrangeFiniteElementSpace
from fealpy.functionspace import  ParametricLagrangeFiniteElementSpace
from fealpy.boundarycondition import DirichletBC
from fealpy.tools.show import showmultirate, show_error_table
from .Parameters import Parameter
from .Utility import WriteMatAndVec
import numpy as np
import random

class PDE:
    def __init__(self,x0,x1,y0,y1,blockx,blocky):
        self.x0 = x0
        self.x1 = x1
        self.y0 = y0
        self.y1 = y1
        self.xstep = (x1-x0)/blockx 
        self.ystep = (y1-y0)/blocky
        self.coef1 = 10**np.random.uniform(0.0,5.0,(blocky+1,blockx+1))
        self.coef2 = 10**np.random.uniform(0.0,5.0,(blocky+1,blockx+1))

    def domain(self):
        return np.array([self.x0, self.x1,self.y0, self.y1])
    
    @cartesian
    def solution(self, p):
        """ 
		The exact solution 
        Parameters
        ---------
        p : 
        Examples
        -------
        p = np.array([0, 1], dtype=np.float64)
        p = np.array([[0, 1], [0.5, 0.5]], dtype=np.float64)
        """
        x = p[..., 0]
        y = p[..., 1]
        pi = np.pi
        val = np.cos(pi*x)*np.cos(pi*y)
        return val # val.shape == x.shape

    @cartesian
    def source(self, p):
        """ 
		The right hand side of convection-diffusion-reaction equation
        INPUT:
            p: array object,  
        """
        x = p[..., 0]
        y = p[..., 1]
        pi = np.pi
        val = 12*pi*pi*np.cos(pi*x)*np.cos(pi*y) 
        val += 2*pi*pi*np.sin(pi*x)*np.sin(pi*y) 
        val += np.cos(pi*x)*np.cos(pi*y)*(x**2 + y**2 + 1) 
        val -= pi*np.cos(pi*x)*np.sin(pi*y) 
        val -= pi*np.cos(pi*y)*np.sin(pi*x)
        return val

    @cartesian
    def gradient(self, p):
        """ 
		The gradient of the exact solution 
        """
        x = p[..., 0]
        y = p[..., 1]
        pi = np.pi
        val = np.zeros(p.shape, dtype=np.float64)
        val[..., 0] = -pi*np.sin(pi*x)*np.cos(pi*y)
        val[..., 1] = -pi*np.cos(pi*x)*np.sin(pi*y)
        return val # val.shape == p.shape

    @cartesian
    def diffusion_coefficient(self, p):
        x = p[..., 0]
        y = p[..., 1]
        xidx = x//self.xstep
        xidx = xidx.astype(np.int)
        yidx = y//self.ystep 
        yidx = yidx.astype(np.int)

        shape = p.shape+(2,)
        val = np.zeros(shape,dtype=np.float64)
        val[...,0,0] = self.coef1[xidx,yidx]
        val[...,0,1] = 0.0

        val[...,1,0] = 0.0
        val[...,1,1] = self.coef2[xidx,yidx]
        return val

    @cartesian
    def convection_coefficient(self, p):
        return np.array([-1.0, -1.0], dtype=np.float64)

    @cartesian
    def reaction_coefficient(self, p):
        x = p[..., 0]
        y = p[..., 1]
        return 1 + x**2 + y**2

    @cartesian
    def dirichlet(self, p):
        return self.solution(p)

def GenerateMat(nx,ny,blockx,blocky, mat_type=None, mat_path=None, need_rhs=False,
                seed=0, meshtype='quad', space_p=1):
    
    np.random.seed(seed)
    random.seed(seed)
    x0 = 0.0
    x1 = 1.0
    y0 = 0.0
    y1 = 1.0
    pde = PDE(x0,x1,y0,y1,blockx,blocky)
    domain = pde.domain()

    if meshtype == 'tri':
        mesh = MF.boxmesh2d(domain, nx=nx, ny=ny, meshtype=meshtype)
        space = LagrangeFiniteElementSpace(mesh, p=space_p)
    elif meshtype == 'quad':
        mesh = MF.boxmesh2d(domain, nx=nx, ny=ny, meshtype=meshtype, p=space_p)
        space = ParametricLagrangeFiniteElementSpace(mesh, p=space_p)

    uh = space.function() 	
    A = space.stiff_matrix(c=pde.diffusion_coefficient)
    B = space.convection_matrix(c=pde.convection_coefficient)
    M = space.mass_matrix(c=pde.reaction_coefficient)
    F = space.source_vector(pde.source)
    A += B 
    A += M
    
    bc = DirichletBC(space, pde.dirichlet)
    A, F = bc.apply(A, F, uh)

    eps = 10**(-15)
    A.data[ np.abs(A.data) < eps ] = 0
    A.eliminate_zeros()
    
    ########################################################
    #            write matrix A and rhs vector F           #
    ########################################################
    WriteMatAndVec(A,F,mat_type,mat_path,need_rhs)

    row_num, col_num = A.shape
    nnz = A.nnz
    return row_num, col_num, nnz

class Para(Parameter):
    def __init__(self):
        super().__init__()

    def AddParas(self):
        self.RandChoose('meshtype',['tri','quad'])
        self.DefineRandInt('space_p',1,4)

        if self.para['space_p'] == 1:
            self.DefineRandInt('nx', 50, 200)
            self.DefineRandInt('blockx',20,40)
        elif self.para['space_p'] == 2:
            self.DefineRandInt('nx', 50, 110)
            self.DefineRandInt('blockx',20,40)
        elif self.para['space_p'] == 3:
            self.DefineRandInt('nx', 40, 70)
            self.DefineRandInt('blockx',20,30)

        self.CopyValue('nx', 'ny')
        self.CopyValue('blockx', 'blocky')

if __name__ == '__main__':
    print('mesh is quad, p=1')
    row_num, col_num, nnz = GenerateMat(200,200,2,2)
    print(row_num, col_num, nnz)

    print('mesh is quad, p=2')
    row_num, col_num, nnz = GenerateMat(110,110,2,2,space_p=2)
    print(row_num, col_num, nnz)

    print('mesh is quad, p=3')
    row_num, col_num, nnz = GenerateMat(70,70,2,2,space_p=3)
    print(row_num, col_num, nnz)


    print('mesh is tri, p=1')
    row_num, col_num, nnz = GenerateMat(200,200,2,2,meshtype='tri')
    print(row_num, col_num, nnz)
    
    print('mesh is tri, p=2')
    row_num, col_num, nnz = GenerateMat(110,110,2,2,meshtype='tri',space_p=2)
    print(row_num, col_num, nnz)
    
    print('mesh is tri, p=3')
    row_num, col_num, nnz = GenerateMat(70,70,2,2,meshtype='tri',space_p=3)
    print(row_num, col_num, nnz)
