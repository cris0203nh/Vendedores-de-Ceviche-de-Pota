import { useEffect, useState } from "react";
import "./App.css";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const sections = [
  ["dashboard","Panel general"],
  ["vendedores","Vendedores"],
  ["licencias","Licencias"],
  ["inspecciones","Inspecciones"],
  ["incumplimientos","Incumplimientos"],
  ["proveedores","Proveedores"],
  ["lotes","Lotes de pota"],
  ["publico","Consulta pública"],
  ["reportes","Reportes ciudadanos"]
];

const empty = {
  vendedores:{nombre:"",documento:"",telefono:"",puesto:"",ubicacion:"",licencia:"Pendiente"},
  inspecciones:{vendedor_id:"",inspector:"",higiene:"Adecuada",temperatura:"",conservacion:"",observaciones:"",resultado:"Pendiente"},
  incumplimientos:{inspeccion_id:"",descripcion:"",evidencia:""},
  proveedores:{nombre:"",documento:"",telefono:"",procedencia:""},
  lotes:{codigo:"",proveedor_id:"",fecha_ingreso:"",especie_declarada:"Pota",cantidad:"",unidad:"kg",procedencia:""},
  reportes:{vendedor_id:"",descripcion:"",tipo:"Sanitario"}
};

const endpoints = {
  vendedores:"/api/vendedores",
  inspecciones:"/api/inspecciones",
  incumplimientos:"/api/incumplimientos",
  proveedores:"/api/proveedores",
  lotes:"/api/lotes",
  publico:"/api/publico/vendedores",
  reportes:"/api/reportes"
};

function App(){
  const [page,setPage] = useState("dashboard");
  const [data,setData] = useState([]);
  const [dashboard,setDashboard] = useState({});
  const [form,setForm] = useState({});
  const [message,setMessage] = useState("");
  const [error,setError] = useState("");
  const [loading,setLoading] = useState(false);

  const load = async () => {
    try{
      const url = page==="dashboard" ? "/api/dashboard" : endpoints[page];
      const response = await fetch(API+url);
      if(!response.ok) throw new Error("No se pudo consultar la API");
      const result = await response.json();
      if(page==="dashboard") setDashboard(result);
      else setData(result);
    }catch(e){setError(e.message);}
  };

  useEffect(()=>{
    setData([]);
    setError("");
    load();
    setForm(empty[page] ? {...empty[page]} : {});
  },[page]);

  const change = (e)=>setForm({...form,[e.target.name]:e.target.value});

  const submit = async(e)=>{
    e.preventDefault();
    setLoading(true);
    setMessage("");
    setError("");
    try{
      let url = endpoints[page];
      let body = {...form};

      if(["vendedor_id","inspeccion_id","proveedor_id","cantidad","temperatura"].some(k=>k in body)){
        for(const key of ["vendedor_id","inspeccion_id","proveedor_id","cantidad","temperatura"]){
          if(body[key]!=="" && body[key]!=null) body[key]=Number(body[key]);
          else if(body[key]==="") body[key]=null;
        }
      }

      const response = await fetch(API+url,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify(body)
      });
      const result = await response.json();
      if(!response.ok) throw new Error(result.detail || "Error al guardar");
      setMessage(result.codigo_seguimiento || result.mensaje || "Registro guardado correctamente");
      setForm({...empty[page]});
      await load();
    }catch(e){setError(e.message);}
    finally{setLoading(false);}
  };

  const fields = {
    vendedores:[
      ["nombre","Nombre completo","text"],["documento","DNI (8 dígitos)","text"],
      ["telefono","Teléfono","text"],["puesto","Nombre del puesto","text"],
      ["ubicacion","Ubicación","text"]
    ],
    inspecciones:[
      ["vendedor_id","ID del vendedor","number"],["inspector","Nombre del inspector","text"],
      ["higiene","Condición de higiene","text"],["temperatura","Temperatura °C","number"],
      ["conservacion","Condición de conservación","text"],["observaciones","Observaciones","text"]
    ],
    incumplimientos:[
      ["inspeccion_id","ID de inspección","number"],
      ["descripcion","Descripción del incumplimiento","text"],
      ["evidencia","Referencia de evidencia","text"]
    ],
    proveedores:[
      ["nombre","Nombre del proveedor","text"],["documento","RUC o documento","text"],
      ["telefono","Teléfono","text"],["procedencia","Procedencia","text"]
    ],
    lotes:[
      ["codigo","Código del lote","text"],["proveedor_id","ID del proveedor","number"],
      ["fecha_ingreso","Fecha de ingreso","date"],
      ["especie_declarada","Especie declarada","text"],
      ["cantidad","Cantidad","number"],["procedencia","Procedencia","text"]
    ],
    reportes:[
      ["vendedor_id","ID del vendedor (opcional)","number"],
      ["descripcion","Descripción de la irregularidad","text"],
      ["tipo","Tipo: Sanitario o Comercial","text"]
    ]
  };

  const update = async(path,body)=>{
    try{
      const r=await fetch(API+path,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
      const j=await r.json();
      if(!r.ok) throw new Error(j.detail || "No se pudo actualizar");
      setMessage(j.mensaje || "Actualizado correctamente");
      await load();
    }catch(e){setError(e.message);}
  };

  const title = sections.find(s=>s[0]===page)?.[1] || "Panel general";

  return <div className="layout">
    <aside className="sidebar">
      <div className="brand"><span>●</span> CevicheSeguro</div>
      <p className="side-label">GESTIÓN DEL SISTEMA</p>
      {sections.map(([id,label])=><button key={id} className={page===id?"nav active":"nav"} onClick={()=>setPage(id)}>{label}</button>)}
      <div className="side-footer">Trazabilidad y control sanitario</div>
    </aside>
    <main className="main">
      <header className="topbar"><div><small>PLATAFORMA DE SUPERVISIÓN</small><h1>{title}</h1></div><span className="online">● Sistema conectado</span></header>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {page==="dashboard" ? <>
        <section className="welcome"><div><span>GESTIÓN SANITARIA Y COMERCIAL</span><h2>Bienvenido a CevicheSeguro</h2><p>Información centralizada para supervisar vendedores, inspecciones y trazabilidad.</p></div></section>
        <div className="cards">
          {Object.entries({Vendedores:dashboard.vendedores,Inspecciones:dashboard.inspecciones,Proveedores:dashboard.proveedores,"Lotes registrados":dashboard.lotes,"Reportes pendientes":dashboard.reportes_pendientes}).map(([k,v])=><article className="metric" key={k}><span>{k}</span><strong>{v ?? "—"}</strong></article>)}
        </div>
        <section className="panel"><h3>Funcionalidades disponibles</h3><p>Registro de comerciantes, control de licencias, inspecciones sanitarias, conservación de la pota, trazabilidad de lotes y reportes ciudadanos.</p></section>
      </> : <>
        {fields[page] && <section className="panel">
          <h3>Registrar información</h3>
          <form onSubmit={submit} className="form">
            {fields[page].map(([name,label,type])=><label key={name}>{label}<input required={!name.includes("vendedor_id") || page!=="reportes"} type={type} name={name} value={form[name]??""} onChange={change} /></label>)}
            <button className="primary" disabled={loading}>{loading?"Guardando...":"Guardar registro"}</button>
          </form>
        </section>}
        {page==="licencias" && <section className="panel"><h3>Actualizar licencia</h3><form className="form" onSubmit={e=>{e.preventDefault();update(`/api/vendedores/${form.id}/licencia`,{estado:form.estado});}}><label>ID vendedor<input required type="number" onChange={e=>setForm({...form,id:e.target.value})}/></label><label>Estado<select onChange={e=>setForm({...form,estado:e.target.value})}><option>Vigente</option><option>Observada</option><option>Vencida</option><option>Pendiente</option></select></label><button className="primary">Actualizar licencia</button></form></section>}
        {page==="lotes" && <section className="panel"><h3>Verificación de lote</h3><form className="form" onSubmit={e=>{e.preventDefault();update(`/api/lotes/${form.id}/verificacion`,{verificacion:form.verificacion,observaciones:form.observaciones||""});}}><label>ID lote<input required type="number" onChange={e=>setForm({...form,id:e.target.value})}/></label><label>Resultado<select onChange={e=>setForm({...form,verificacion:e.target.value})}><option>Verificado</option><option>Observado</option><option>Pendiente</option></select></label><label>Observaciones<input onChange={e=>setForm({...form,observaciones:e.target.value})}/></label><button className="primary">Guardar verificación</button></form></section>}
        {page==="reportes" && <section className="panel"><h3>Atender reporte ciudadano</h3><form className="form" onSubmit={e=>{e.preventDefault();update(`/api/reportes/${form.id}`,{estado:form.estado,respuesta:form.respuesta||""});}}><label>ID reporte<input required type="number" onChange={e=>setForm({...form,id:e.target.value})}/></label><label>Estado<select onChange={e=>setForm({...form,estado:e.target.value})}><option>En revisión</option><option>Atendido</option><option>Rechazado</option></select></label><label>Respuesta<input onChange={e=>setForm({...form,respuesta:e.target.value})}/></label><button className="primary">Actualizar reporte</button></form></section>}
        <section className="panel"><div className="panel-head"><h3>Registros</h3><button className="secondary" onClick={load}>Actualizar</button></div>
          <div className="table-wrap"><table><thead><tr>{data[0]?Object.keys(data[0]).map(k=><th key={k}>{k.replaceAll("_"," ")}</th>):<th>Sin registros todavía</th>}</tr></thead><tbody>{data.map((row,i)=><tr key={i}>{Object.values(row).map((v,j)=><td key={j}>{v??"—"}</td>)}</tr>)}</tbody></table></div>
        </section>
      </>}
      <footer>CevicheSeguro · Sistema de trazabilidad y control sanitario</footer>
    </main>
  </div>;
}

export default App;
