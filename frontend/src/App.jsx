import { useEffect, useState } from "react";
import "./App.css";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function App() {
  const [vendedores, setVendedores] = useState([]);
  const [puestos, setPuestos] = useState([]);
  const [form, setForm] = useState({
    vendedor_id: "",
    nombre_puesto: "",
    ubicacion: ""
  });
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  async function cargarDatos() {
    try {
      const [rv, rp] = await Promise.all([
        fetch(`${API}/api/vendedores`),
        fetch(`${API}/api/puestos`)
      ]);

      if (!rv.ok) throw new Error("No se pudieron consultar los vendedores.");
      if (!rp.ok) throw new Error("No se pudieron consultar los puestos.");

      setVendedores(await rv.json());
      setPuestos(await rp.json());
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    cargarDatos();
  }, []);

  function cambiarCampo(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function registrar(e) {
    e.preventDefault();
    setMensaje("");
    setError("");
    setCargando(true);

    try {
      const response = await fetch(`${API}/api/puestos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vendedor_id: Number(form.vendedor_id),
          nombre_puesto: form.nombre_puesto.trim(),
          ubicacion: form.ubicacion.trim()
        })
      });

      const resultado = await response.json();

      if (!response.ok) {
        throw new Error(
          response.status === 409
            ? "Este puesto ya se encuentra registrado para el vendedor."
            : resultado.detail || "No se pudo registrar el puesto."
        );
      }

      setMensaje(`Puesto registrado correctamente. Código: ${resultado.id}`);
      setForm({ vendedor_id: "", nombre_puesto: "", ubicacion: "" });
      await cargarDatos();
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <main className="app">
      <header className="header">
        <div className="brand-mark">CS</div>
        <div>
          <p className="eyebrow">CEVICHESEGURO · GESTIÓN COMERCIAL</p>
          <h1>Registro de puestos de venta</h1>
          <p className="subtitle">
            Administra la ubicación de los puestos asociados a cada vendedor.
          </p>
        </div>
      </header>

      <section className="content">
        <div className="form-panel">
          <div className="section-heading">
            <span className="step">HU-02</span>
            <h2>Registrar nuevo puesto</h2>
          </div>

          <form onSubmit={registrar}>
            <label htmlFor="vendedor_id">Vendedor registrado *</label>
            <select
              id="vendedor_id"
              name="vendedor_id"
              value={form.vendedor_id}
              onChange={cambiarCampo}
              required
            >
              <option value="">Seleccionar vendedor</option>
              {vendedores.map(v => (
                <option key={v.id} value={v.id}>
                  {v.nombre} — ID {v.id}
                </option>
              ))}
            </select>

            <label htmlFor="nombre_puesto">Nombre del puesto *</label>
            <input
              id="nombre_puesto"
              name="nombre_puesto"
              value={form.nombre_puesto}
              onChange={cambiarCampo}
              placeholder="Ej. Puesto Mercado Central"
              minLength={2}
              maxLength={120}
              required
            />

            <label htmlFor="ubicacion">Ubicación del puesto *</label>
            <input
              id="ubicacion"
              name="ubicacion"
              value={form.ubicacion}
              onChange={cambiarCampo}
              placeholder="Ej. Mercado Central, Lima"
              minLength={3}
              maxLength={200}
              required
            />

            <p className="required-note">* Todos los campos son obligatorios.</p>

            <button type="submit" disabled={cargando || vendedores.length === 0}>
              {cargando ? "Guardando..." : "Registrar puesto"}
            </button>
          </form>

          {vendedores.length === 0 && (
            <p className="notice">
              Primero debe existir un vendedor registrado para asociarle un puesto.
            </p>
          )}

          {mensaje && <div className="success">{mensaje}</div>}
          {error && <div className="error">{error}</div>}
        </div>

        <div className="list-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">PADRÓN COMERCIAL</p>
              <h2>Puestos registrados</h2>
            </div>
            <span className="counter">{puestos.length}</span>
          </div>

          {puestos.length === 0 ? (
            <div className="empty">
              <span>▤</span>
              <p>Aún no hay puestos registrados.</p>
            </div>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Código</th>
                    <th>Vendedor</th>
                    <th>Puesto</th>
                    <th>Ubicación</th>
                  </tr>
                </thead>
                <tbody>
                  {puestos.map(p => (
                    <tr key={p.id}>
                      <td>PV-{String(p.id).padStart(4, "0")}</td>
                      <td>{p.vendedor}</td>
                      <td>{p.nombre_puesto}</td>
                      <td>{p.ubicacion}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="footnote">
            Cada puesto se encuentra asociado al identificador de su vendedor.
          </p>
        </div>
      </section>
      <footer>CevicheSeguro · Registro y trazabilidad de comerciantes</footer>
    </main>
  );
}

export default App;
