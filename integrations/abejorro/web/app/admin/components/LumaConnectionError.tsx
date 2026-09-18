import { Button } from '@/components/ui/Button';
import { API_BASE_URL } from '@/lib/http-client';

interface Props {
  error: string;
  retry: () => void;
  busy?: boolean;
  hasPreviousData?: boolean;
}

export function LumaConnectionError({
  error,
  retry,
  busy,
  hasPreviousData,
}: Props) {
  const networkFailure =
    /failed to fetch|networkerror|network request failed|load failed/i.test(
      error
    );
  const authenticationFailure = error === 'No authenticated';
  let destination = '/api/admin/luma/sesiones';
  let local = false;
  try {
    const url = new URL(
      `${API_BASE_URL}/api/admin/luma/sesiones`,
      'http://localhost'
    );
    destination = `${url.origin}${url.pathname}`;
    local = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
  } catch {
    /* Do not expose invalid configuration or credentials. */
  }
  const title = authenticationFailure
    ? 'Necesitas iniciar sesión'
    : networkFailure
      ? 'No se pudo conectar con el servicio de sesiones'
      : 'No se pudieron actualizar las sesiones';
  const description = authenticationFailure
    ? 'No hay una credencial de acceso disponible. Entra al administrador y vuelve a abrir Luma.'
    : networkFailure
      ? 'El navegador no recibió una respuesta accesible del servidor. Esto no significa que las sesiones se hayan borrado.'
      : 'El servicio no pudo completar la consulta. Esto no equivale a una lista vacía de sesiones.';
  return (
    <section
      role="alert"
      className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-slate-800 space-y-3"
    >
      <h3 className="font-semibold text-base">{title}</h3>
      <p className="text-sm leading-relaxed">{description}</p>
      <p className="text-sm leading-relaxed">
        {networkFailure
          ? local
            ? 'Esta vista está configurada para una API local. Comprueba que esté iniciada y que permita conexiones desde la dirección de este panel.'
            : 'Comprueba tu conexión y reintenta. Si continúa, revisa la disponibilidad del servicio y los permisos de conexión del navegador.'
          : authenticationFailure
            ? 'Usa el mismo acceso del administrador de Abejorro.'
            : 'Reintenta la consulta. Si persiste, revisa la respuesta y los registros del servicio.'}
      </p>
      {hasPreviousData && (
        <p className="text-sm font-medium">
          La lista de abajo conserva la última respuesta recibida; puede estar
          desactualizada.
        </p>
      )}
      <details className="text-xs text-slate-600">
        <summary className="cursor-pointer py-1">Detalles de conexión</summary>
        <dl className="mt-2 space-y-2">
          <div>
            <dt className="font-semibold">Consulta</dt>
            <dd className="break-all">{destination}</dd>
          </div>
          <div>
            <dt className="font-semibold">Resultado</dt>
            <dd>
              {networkFailure
                ? 'Sin respuesta HTTP accesible. El navegador no distingue aquí entre servidor inaccesible, bloqueo CORS, TLS o red.'
                : authenticationFailure
                  ? 'Credencial de acceso no disponible.'
                  : error}
            </dd>
          </div>
        </dl>
      </details>
      <div className="flex flex-wrap gap-3">
        {authenticationFailure ? (
          <a href="/admin/login" className="underline font-medium text-sm">
            Ir al inicio de sesión
          </a>
        ) : (
          <Button variant="outline" size="sm" onClick={retry} disabled={busy}>
            {busy ? 'Reintentando…' : 'Reintentar conexión'}
          </Button>
        )}
      </div>
    </section>
  );
}
