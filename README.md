# MesaChef Studio para GitHub Pages

Versión web estática de MesaChef Studio: conserva recetas, menús, despensa, compra y las herramientas Rescate, ¿Y si…?, Envases y Cocina agrupada. No necesita el servidor ni el inicio de sesión de ChatGPT.

## Publicación

El repositorio del usuario es `angelmunizpedraza/mesachef-studio`, público y con Pages habilitado. La integración de GitHub de esta sesión rechazó la escritura (403); ningún archivo fue enviado a ese repositorio. Se ha preparado también una publicación con un único workflow que descarga este paquete público y verifica su SHA-256. El usuario debe confirmar ese archivo en la rama main para iniciar Actions. El workflow inicial descarga y verifica el ZIP una sola vez, guarda el código completo en la rama main y publica Pages. Las siguientes ejecuciones usan ese código del repositorio y guardan las consultas actualizadas, sin sobrescribirlo con el ZIP inicial. No necesita volver a conectar ChatGPT.


1. Crear un repositorio llamado `mesachef-studio`, con rama `main`, en tu cuenta de GitHub. No subir copias personales, tokens ni contraseñas.
2. Subir el contenido de este proyecto al repositorio, incluyendo `.github/workflows/pages.yml`.
3. En **Settings → Pages → Build and deployment → Source**, seleccionar **GitHub Actions**.
4. En **Actions → Publicar MesaChef Studio**, ejecutar **Run workflow**. Tras terminar, GitHub muestra la dirección publicada en el entorno `github-pages`.

Las rutas funcionan en una dirección de proyecto como `https://TU_USUARIO.github.io/mesachef-studio/` y en la raíz de un dominio propio. El ejemplo de URL anterior no es una web ya publicada: falta asociarla a una cuenta real.

GitHub Pages suele publicar la web en internet aunque el repositorio sea privado, según el plan. El código y el catálogo no contienen tus menús ni tu despensa: los datos personales se guardan exclusivamente en el navegador y no se suben a GitHub. Pages de repositorios privados depende de la disponibilidad de tu plan; no se garantiza publicación privada.

## Precios reales y sus fechas

GitHub Pages no ejecuta un servidor de precios. La tarea de GitHub Actions consulta la API pública oficial de Mercadona cada seis horas y en cada publicación. Confirma código postal y almacén, consulta las fichas del catálogo y publica `site/market/CP.json` con la hora real de cada consulta. No contiene claves ni utiliza intermediarios.

Configuración inicial: Sevilla `41011` y Madrid `28001`. Se pueden añadir códigos postales a `scripts/postcodes.json`; el supermercado debe confirmar cobertura. La lista de productos compatibles está en `scripts/product-map.json`.

**Actualizar en la app descarga la última consulta publicada**, no hace una consulta en directo al supermercado. GitHub puede retrasar las tareas programadas o desactivarlas por inactividad; hay que revisar Actions si dejan de actualizarse. Si falla la fuente, el despliegue conserva las fichas incluidas en el repositorio con sus fechas originales. Si superan 24 horas, la app deja de incluirlas como precios vigentes. No inventa importes.

El precio de los productos al peso sigue pendiente de su cantidad real. Los importes de ticket introducidos a mano están identificados como manuales. Los precios incluyen producto, fuente, zona y fecha; el total excluye gastos de envío y básicos no listados.

## Catálogos de supermercados

La sección **Supermercados** busca productos por nombre, marca, referencia y categoría, con filtros de tienda y precio aplicable al CP, además de ordenación por €/kg o €/L sin mezclar unidades. Tiene una compra independiente, fichas con fuente, copias de seguridad y una pantalla de cobertura. No impone cupos de productos guardados; la capacidad depende del navegador.

Consultas incluidas: 10–11 de octubre de 2026. Cada ficha conserva su fecha individual.

| Cadena | Fichas | Alcance comprobado |
| --- | ---: | --- |
| Mercadona | 4.269 | 152 de 152 categorías online, CP 41011, almacén svq1. El surtido físico puede diferir. |
| Día | 5.808 | 284 de 290 categorías; 6 pendientes o fallidas y 1935 referencias del índice sin ficha. Zona sin confirmar. |
| Carrefour | 54 | Productos visibles en su portada; cobertura parcial y zona sin confirmar. |
| MAS | 2.992 | Primeras páginas de 165 de 566 categorías. Faltan páginas y zona confirmada. |
| Alcampo, Lidl, ALDI, Cash Fresh, Covirán, El Corte Inglés/Supercor | 0 | Enlaces oficiales, sin productos integrados todavía. |

**No contiene todos los productos de Sevilla ni de España.** El directorio inicial de diez cadenas tampoco es una lista exhaustiva de supermercados españoles. Una categoría consultada no garantiza stock de una tienda física. El índice de Día y sus faltantes están publicados en el propio catálogo; algunos recorridos de paginación quedan pendientes.

Actions consulta las fuentes públicas mediante `refresh-catalogs.py`, `refresh-dia.py` y `refresh-mas.py`. Las primeras páginas de MAS son parciales: su paginación por parámetros se deja fuera. Día y MAS guardan cada avance; una consulta que falla conserva las fichas anteriores con su fecha real. Si fallan, se conservan las fichas anteriores con su fecha. Los totales solo suman precios de menos de 24 horas, sin condiciones, de envases de precio fijo y zona confirmada. Los precios de las otras zonas siguen visibles como referencia y quedan pendientes en el total. Las copias importadas requieren volver a cargar las fuentes antes de usar sus precios.

## Trasladar tus datos desde la web anterior

1. En la web anterior, abrir **Preferencias → Exportar copia de seguridad**.
2. En GitHub Pages, abrir **Preferencias → Restaurar copia** y elegir el JSON descargado.
3. Confirmar la restauración. La app carga las fichas publicadas para el CP de la copia antes de usar esos precios como vigentes.

Los datos se separan por repositorio y navegador. Cambiar de dominio, móvil o navegador requiere importar una copia; no existe sincronización en la nube. La capacidad disponible depende del navegador, sin los antiguos cupos de menús, favoritos, extras o recetas personales.

## Instalación y uso sin conexión

Abrir la dirección publicada por HTTPS. En Chrome Android usar **Añadir a pantalla de inicio / Instalar aplicación**. En Safari iPhone usar **Compartir → Añadir a pantalla de inicio**. Tras una apertura con conexión, el service worker guarda la interfaz y las imágenes para uso local. Las consultas de precios quedan fuera de su caché.

## Validación

- `python scripts/validate-site.py`: comprueba rutas, manifiesto, archivos y catálogo fechado.
- `python -m unittest discover -s tests -p '*_test.py'`: confirma cobertura, fallo de fuente, errores por producto y ausencia de datos inventados.
- `npm install` seguido de `npm test`: motor, formularios y navegación en DOM emulado, almacenamiento por repositorio, descarga de fichas, fechas y service worker.
- `python scripts/refresh-prices.py`: consulta real de los códigos postales configurados.

El acabado visual, la instalación y el uso sin conexión en un móvil físico no se han comprobado en un navegador real en esta sesión. El resultado de cada despliegue y su dirección se pueden consultar en Actions y en el entorno github-pages del repositorio.
