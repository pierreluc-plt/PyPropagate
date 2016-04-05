
def add_coordinate(settings,category,name):

    import expresso.pycas as pc

    x = category.create_key(name,pc.Symbol(name,type=pc.Types.Real),info='coordinate')
    xmin = category.create_key('%smin' % name,pc.Symbol('%s_min' % name),info='minimum value')
    xmax = category.create_key('%smax' % name,pc.Symbol('%s_max' % name),info='maximum value')
    xi = category.create_key('%si' % name,pc.Symbol('%s_i' % name,type=pc.Types.Natural),info='numerical index')
    Nx = category.create_key('N%s' % name,pc.Symbol('N_%s' % name,type=pc.Types.Natural),info='numerical steps')
    sx = category.create_key('s%s' % name,pc.Symbol('s_%s' % name),info='total size')
    dx = category.create_key('d%s' % name,pc.Symbol('\Delta %s' % name),info='step size')

    setattr(category,name, xmin + xi * dx)
    setattr(category,'s%s' % name,xmax - xmin)
    setattr(category,'d%s' % name,sx/(Nx-1))

    category.lock(name,'defined by %si' % name)
    category.lock('s%s' % name,'defined by %smin and %smax' % (name,name))
    category.lock('d%s' % name,'defined by s%s and N%s' % (name,name))

    settings.unitless.add_key('%s_coordinate' % name,x)

def add_time_symbols(settings):
    settings.simulation_box.unlock()
    add_coordinate(settings,settings.simulation_box,'t')
    sb  = settings.simulation_box
    sb.tmin = 0
    sb.export(settings.symbols,warn=False)

    if settings.has_category('wave_equation'):
        settings.wave_equation.create_function('u0',(sb.x,sb.y,sb.z,sb.t))
        settings.partial_differential_equation.u0 = settings.wave_equation.u0.subs(sb.t,0)

def add_simulation_box_symbols(settings):
    from expresso.pycas import Symbol,symbols,Function,pi,I,Types,sqrt
    import expresso.pycas as pc
    import types

    sb = settings.create_category("simulation_box",info="parameters and dimensions of the simulation box")

    for c in 'x,y,z'.split(','):
        add_coordinate(settings,sb,c)

    sb.create_key("nx", Symbol("n_x",type = Types.Integer,positive=True),sb.Nx - 2,info="voxels in x direction minus the boundary conditions")
    sb.create_key("ny", Symbol("n_y",type = Types.Integer,positive=True),sb.Ny - 2,info="voxels in y direction minus the boundary conditions")
    sb.create_key("nz", Symbol("n_z",type = Types.Integer,positive=True),sb.Nz - 1,info="voxels in z direction minus the boundary condition")

    sb.create_key('r',Function('r')(sb.x,sb.y),sqrt(sb.x**2+sb.y**2),info='distance from origin')

    sb.create_key("coordinates",(sb.x,sb.y,sb.z))
    sb.lock('coordinates')

    sb.lock()

    def set_size(self,axis_name,size):
        sb.unlock("%smin" % axis_name)
        sb.unlock("%smax" % axis_name)

        if axis_name in 't,z':
            setattr(self,"%smin" % axis_name,0)
            setattr(self,"%smax" % axis_name,size)
        else:
            setattr(self,"%smin" % axis_name,-size/2)
            setattr(self,"%smax" % axis_name,size/2)

        sb.lock("%smin" % axis_name,'defined by s%s' % axis_name)
        sb.lock("%smax" % axis_name,'defined by s%s' % axis_name)

    def set_vsize(self,axis_name,size):
        setattr(self,"N%s" % axis_name,size)

    def set_physical_size(self,*sizes):
        'Sets the physical box size of the simulation in x, y and z direction'
        if len(sizes) == 2:
            self.set_size('x',sizes[0])
            self.set_size('z',sizes[1])
        elif len(sizes) == 3:
            self.set_size('x',sizes[0])
            self.set_size('y',sizes[1])
            self.set_size('z',sizes[2])
        else:
            raise ValueError('set_physical_size takes 2 or 3 arguments')

    def set_voxel_size(self,*sizes):
        'Sets the voxe size of the simulation in x, y and z direction'
        if len(sizes) == 2:
            self.set_vsize('x',sizes[0])
            self.set_vsize('z',sizes[1])
        elif len(sizes) == 3:
            self.set_vsize('x',sizes[0])
            self.set_vsize('y',sizes[1])
            self.set_vsize('z',sizes[2])
        else:
            raise ValueError('set_voxel_size takes 2 or 3 arguments')

    def set_method(self,physical_size,voxel_size):
        """Sets the simulation box size using the physical_size and voxel_size arguments which are 3-tupels containing the simulation box dimensions in x, y, and z directions."""
        self.set_physical_size(*physical_size)
        self.set_voxel_size(*voxel_size)

    sb._set_attribute('set_size',types.MethodType(set_size,sb))
    sb._set_attribute('set_vsize',types.MethodType(set_vsize,sb))

    sb._set_attribute('set_physical_size',types.MethodType(set_physical_size,sb))
    sb._set_attribute('set_voxel_size',types.MethodType(set_voxel_size,sb))
    sb._set_attribute('set', types.MethodType(set_method,sb))

    def make_unitless(settings):
        sb = settings.simulation_box

        from units import get_unit
        defined = set()

        for s in settings.get_numeric((sb.sx,sb.sy,sb.sz)):
            unit = get_unit(s,cache = settings.get_cache())

            if unit is None or unit in defined or unit.is_function:
                continue

            defined.add(unit)
            unit_name = str(unit)
            if not settings.unitless.has_name(unit_name):
                settings.unitless.create_key(unit_name,unit)
            setattr(settings.unitless,unit_name,(2*unit/s).evaluate(cache=settings.get_cache()))

    settings.initializers['make_unitless'] = make_unitless


def add_partial_differential_equation_symbols(settings):
    import expresso.pycas as pc
    sb = settings.simulation_box
    pde = settings.create_category('partial_differential_equation',short_name='PDE',info="parameters of the partial differential equation")

    pde.create_function('A',sb.coordinates)
    pde.create_function('C',sb.coordinates,pde.A)
    pde.create_function('F',sb.coordinates)

    pde.create_function('ra',sb.coordinates,pde.A*sb.dz/sb.dx**2,info="finite difference paramter")
    pde.create_function('rc',sb.coordinates,pde.C*sb.dz/sb.dy**2,info="finite difference paramter")
    pde.create_function('rf',sb.coordinates,pde.F*sb.dz/2,info="finite difference paramter")

    pde.create_function('u',sb.coordinates,info='solution to the PDE')
    pde.lock('u')

    pde._set_attribute('equation',pc.equal(pc.derivative(pde.u,sb.z), pde.A * pc.derivative(pc.derivative(pde.u,sb.x),sb.x) +  pde.C * pc.derivative(pc.derivative(pde.u,sb.y),sb.y)  + pde.F * pde.u ))

    pde.create_key('u0',pc.Function('u_0_PDE')(*sb.coordinates),info="field initial condition")
    pde.create_function('u_boundary',sb.coordinates,info="field boundary condition");

    pde.lock()

def create_paraxial_settings():
    from .settings import Settings
    settings = Settings('settings for solving the paraxial differential equation')
    add_simulation_box_symbols(settings)
    settings.simulation_box.export(settings.symbols)
    add_partial_differential_equation_symbols(settings)
    settings.partial_differential_equation.export(settings.symbols)
    return settings

def add_wave_equation_symbols(settings):
    import units
    from expresso.pycas import Function,Symbol,Types,pi

    s = settings.simulation_box

    c = settings.numerics.create_key('c',Symbol('c'),units.c,info='speed of light')
    h = settings.numerics.create_key('h',Symbol('h'),units.h,info='Planck\'s constant')
    hbar = settings.numerics.create_key('hbar',Symbol('hbar'),units.hbar,info='reduced Planck\'s constant')

    we = settings.create_category("wave_equation",info="parameters for solving the wave equation",short_name="WE")

    n = we.create_key("n",Function("n")(*s.coordinates))

    omega = we.create_key('omega',Symbol('omega'),info='angular wave frequency')
    wavelength = we.create_key('wavelength',Function("lambda")(omega),settings.numerics.c/(2*pi*omega),info='vacuum wavelength')
    k = we.create_key("k",Function("k")(omega),omega/settings.numerics.c,info='wave number')
    E = we.create_key("E",Function("E")(omega),omega * settings.numerics.hbar,info='photon energy')

    we.lock('k','defined by omega')
    we.lock('E','defined by omega')

    def set_energy(settings,value):
        we.unlock('E')
        we.omega = we.E / hbar
        we.lock('omega','defined by energy')
        we.E = value

    import types
    we._set_attribute('set_energy',types.MethodType( set_energy, settings ) )

def create_paraxial_wave_equation_settings():

    from .settings import Settings
    settings = Settings('settings for solving the paraxial differential equation')

    add_simulation_box_symbols(settings)
    settings.simulation_box.export(settings.symbols)

    add_wave_equation_symbols(settings)
    settings.wave_equation.export(settings.symbols)

    add_partial_differential_equation_symbols(settings)
    settings.partial_differential_equation.export(settings.symbols)

    from expresso.pycas import I

    pe = settings.partial_differential_equation
    s = settings.symbols
    pe.F = I*s.k/2*(s.n**2-1)
    pe.A = I/(2*s.k)

    pe.lock('F','defined by wave equation')
    pe.lock('A','defined by wave equation')
    s.remove_name("F")
    s.remove_name("A")

    return settings

def set_plane_wave_initial_conditions(settings):
    """Sets the intial conditions to a plane wave with intensity 1.
    The boundary are set to the index of refraction at z=0."""
    from expresso.pycas import exp

    s = settings.simulation_box
    pe = settings.partial_differential_equation

    pe.u0 = 1
    pe.u_boundary = pe.u0.subs(s.z,0) * exp(pe.F.subs(s.z,0)*s.z)

def create_next_settings(old_settings):
    settings = old_settings.copy(copy_initializers = False,copy_updaters = False)

    sb = settings.simulation_box
    sb.unlock('zmin')
    sb.unlock('zmax')
    sb.unlock('sz')

    sb.zmin = old_settings.get_numeric(sb.zmax)
    sb.zmax = sb.zmin + sb.sz

    sb.lock('zmin','defined by previous simulation')
    sb.lock('zmax','defined by zmin and sz')

    return settings

def add_padding(array,factor,mode = 'edge',**kwargs):
    import numpy as np
    from coordinate_ndarray import CoordinateNDArray

    padding_points = [[int(x*factor)]*2 for x in array.data.shape]
    new_data = np.pad(array.data,padding_points,mode,**kwargs)

    extension = [d*p[0] for d,p in zip(array._dbounds,padding_points)]
    new_bounds = [(b-i,e+i) for i,(b,e) in zip(extension,array.bounds)]

    return CoordinateNDArray(new_data,new_bounds,array.axis,array.evaluate)

def set_initial(settings,initial_array):
    import expresso.pycas as pc
    from coordinate_ndarray import CoordinateNDArray

    if isinstance(initial_array,CoordinateNDArray):
        initial = pc.array("initial",initial_array.data)
    else:
        initial = pc.array("initial",initial_array)

    sb = settings.simulation_box

    if tuple(initial_array.axis) == (sb.x,):
        settings.partial_differential_equation.u0 = initial(sb.xi)
    elif tuple(initial_array.axis) == (sb.x,sb.y):
        settings.partial_differential_equation.u0 = initial(sb.yi,sb.xi)
        sb.Ny = initial_array.shape[1]
        if isinstance(initial_array,CoordinateNDArray):
            sb.unlock('ymin')
            sb.unlock('ymax')
            sb.unlock('sy')
            sb.ymin = initial_array.bounds[1][0]
            sb.ymax = initial_array.bounds[1][1]
            sb.sy = sb.ymax - sb.ymin
            sb.lock('ymin','defined by initial array')
            sb.lock('ymax','defined by initial array')
            sb.lock('sy','defined by ymin and ymax')

    else:
        raise ValueError('initial array axis must be (x,) or (x,y)')

    sb.Nx = initial_array.shape[0]

    if isinstance(initial_array,CoordinateNDArray):
        sb.unlock('xmin')
        sb.unlock('xmax')
        sb.unlock('sx')
        sb.xmin = initial_array.bounds[0][0]
        sb.xmax = initial_array.bounds[0][1]
        sb.sx = sb.xmax - sb.xmin
        sb.lock('xmin','defined by initial array')
        sb.lock('xmax','defined by initial array')
        sb.lock('sx','defined by xmin and xmax')

def get_refraction_indices(material,min_energy,max_energy,steps):
    from mechanize import Browser

    max_steps = 499

    if steps > max_steps:
        dn = (max_energy - min_energy)/(steps - 1)
        max = min_energy + max_steps * dn
        return get_refraction_indices(material,min_energy,max,max_steps) + \
               get_refraction_indices(material,min_energy+dn,max_energy,steps-max_steps)

    br = Browser()

    br.open( "http://henke.lbl.gov/optical_constants/getdb.html" )

    br.select_form(nr=0)

    br.form[ 'Formula' ] = material
    br.form[ 'Min' ] = str(min_energy)
    br.form[ 'Max' ] = str(max_energy)
    br.form[ 'Npts' ] = str(steps-1)
    br.form[ 'Output' ] = ['Text File']

    res = br.submit().read()

    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def get_numbers(line):
        return [float(v) for v in line.split(' ') if is_number(v)]

    try:
        betadelta = [get_numbers(line) for line in res.split('\n') if len(get_numbers(line)) == 3]
        values = [1-float(v[1])+1j*float(v[2]) for v in betadelta]
    except:
        betadelta = []

    if len(betadelta) != steps:
        raise RuntimeError('error retrieving refractive index for %s\nserver response: %s' % (material,res))

    return values

def create_material(name,settings):

    import expresso.pycas as pc

    nname = 'n_%s' % name

    if not settings.has_category('refractive_indices'):
        settings.create_category('refractive_indices')
    r = settings.refractive_indices

    omega = settings.wave_equation.omega

    def init_material(settings):

        import units
        import numpy as np

        sb = settings.simulation_box
        r = settings.refractive_indices
        omega = settings.wave_equation.omega

        if hasattr(sb,'t'):
            N = settings.get_as(sb.Nt,int)
            omega_0 = settings.get_numeric(omega)

            omegamin = -2*pc.pi*N/sb.st + omega_0
            omegamax =  2*pc.pi*N/sb.st + omega_0
            domega  = (omegamax - omegamin)/(N-1)
            omega_i = (omega - omegamin )/domega

            EminExpr = abs(omegamin * units.hbar / units.eV)
            EmaxExpr = abs(omegamax * units.hbar / units.eV)
        else:
            N = 3
            E = units.hbar * omega / units.eV
            EmaxExpr = E + 1
            EminExpr = E - 1
            omega_i = 1
        try:
            Emin = settings.get_as(EminExpr,float)
            Emax = settings.get_as(EmaxExpr,float)
        except:
            return

        if Emax < Emin:
            Emax,Emin = Emin,Emax

        key = (N,Emin,Emax)
        if not hasattr(r,'_cache'):
            r._set_attribute('_cache',{})
        else:
            if nname in r._cache and r._cache[nname] == key:
                return
        r._cache[nname] = key

        narr = pc.array(nname,np.array(get_refraction_indices(name,Emax,Emin,N)))
        setattr(r,nname,narr(omega_i))


    settings.initializers["init_" + nname] = init_material

    if r.has_name(nname):
        return getattr(r,nname)
    return r.create_key(nname,pc.Function(nname)(omega,))

def create_2D_frequency_settings(settings):
    import expresso.pycas as pc
    import units
    from .plot import expression_to_field
    from .coordinate_ndarray import CoordinateNDArray
    import numpy as np

    freq_settings = create_paraxial_settings()

    sb = settings.simulation_box
    we = settings.wave_equation

    pde = freq_settings.partial_differential_equation

    omega0 = settings.get_numeric(we.omega)
    k0 = settings.get_numeric(we.k)

    freq_settings.simulation_box.unlock()
    freq_settings.simulation_box.remove_name('y')
    omega = freq_settings.simulation_box.create_key('y',pc.Symbol('omega'))

    fsb = freq_settings.simulation_box
    freq_settings.simulation_box.y = fsb.ymin + fsb.yi * fsb.dy

    omega_def = settings.get_definition(we.omega)
    reason = False
    if we.omega in settings.locked_keys:
        reason = settings.locked_keys[we.omega]
        we.unlock('omega')
    we.omega = None

    n = settings.get_numeric(we.n.subs(sb.y,0)).subs(omega,abs(omega - omega0))
    parameter = freq_settings.create_category('paramter')
    parameter.create_function('n',(omega,),n)

    we.omega = omega_def
    if reason is not False:
        we.lock('omega',reason)

    pde.A = 1j/(2*k0)
    pde.C = 0
    pde.F = 1j/(2*k0) * (n**2*(omega - omega0)**2/units.c**2 - k0**2)

    xmin = settings.get_numeric(sb.xmin)
    xmax = settings.get_numeric(sb.xmax)

    freq_settings.simulation_box.xmin = xmin
    freq_settings.simulation_box.xmax = xmax
    freq_settings.simulation_box.Nx = settings.get_as(sb.Nx,int)

    omegamin = settings.get_numeric(-2*pc.pi*sb.Nt/sb.st)
    omegamax = settings.get_numeric( 2*pc.pi*sb.Nt/sb.st)

    freq_settings.simulation_box.ymin = omegamin
    freq_settings.simulation_box.ymax = omegamax
    freq_settings.simulation_box.Ny = settings.get_as(sb.Nt,int)

    freq_settings.simulation_box.zmin = settings.get_numeric(sb.zmin)
    freq_settings.simulation_box.zmax = settings.get_numeric(sb.zmax)
    freq_settings.simulation_box.Nz = settings.get_as(sb.Nz,int)

    freq_settings.unitless.create_key('s',units.s,settings.get_as( 2/(omegamax - omegamin)/units.s , float ) )

    u0 = expression_to_field(settings.wave_equation.u0.subs([(sb.y,0),(sb.z,sb.zmin)]), settings )

    u0hat = CoordinateNDArray( np.fft.fftshift( np.fft.fft(u0.data,axis=1) , axes=(1,) ) ,
                               [(xmin,xmax),( omegamin, omegamax )] ,
                               [sb.x,omega])

    set_initial(freq_settings,u0hat)
    freq_settings.partial_differential_equation.u_boundary = 0

    return freq_settings

