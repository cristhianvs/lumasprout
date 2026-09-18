import { LumaConnectionError } from './LumaConnectionError';
import { Button } from '@/components/ui/Button';
import type { LumaSesion } from '@/lib/lumaApi';
import { LUMA_INTERVALO_SONDEO_LISTA_MS } from '@/lib/lumaConstantes';
import { LumaSesionesTabla } from './LumaSesionesTabla';

interface LumaVistaSesionesProps {
  sesiones: LumaSesion[] | null;
  /**
   * false: la API respondio 200 pero con una forma que el cliente no reconoce. Nunca se
   * trata igual que "sesiones vacio de verdad": una vale "sin datos", la otra "algo esta
   * roto en la integracion" (ver nota en lib/adminApi.ts sobre el bug de 2026-09-18).
   */
  formaReconocida: boolean;
  isLoading: boolean;
  error: string | null;
  onActualizar: () => void;
  onSeleccionar: (runId: string) => void;
}

export function LumaVistaSesiones({
  sesiones,
  formaReconocida,
  isLoading,
  error,
  onActualizar,
  onSeleccionar,
}: LumaVistaSesionesProps) {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <p className="text-sm text-gray-500">
          Sesiones de LumaSprout. La lista se actualiza sola cada{' '}
          {LUMA_INTERVALO_SONDEO_LISTA_MS / 1000} s.
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={onActualizar}
          disabled={isLoading}
        >
          {isLoading ? 'Actualizando...' : 'Actualizar'}
        </Button>
      </div>

      {isLoading && sesiones === null && !error && (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="animate-pulse text-gray-500">
            Cargando sesiones...
          </div>
        </div>
      )}

      {error && (
        <LumaConnectionError
          error={error}
          retry={onActualizar}
          busy={isLoading}
          hasPreviousData={sesiones !== null && formaReconocida}
        />
      )}

      {sesiones !== null && !error && !formaReconocida && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
          La API respondió correctamente, pero con un formato de datos que esta
          pantalla no reconoce. Esto NO significa que no haya sesiones: es un
          problema de integración que hay que revisar, no lo confundas con
          &quot;todavía no hay sesiones registradas&quot;.
        </div>
      )}

      {sesiones !== null && formaReconocida && (
        <LumaSesionesTabla sesiones={sesiones} onSeleccionar={onSeleccionar} />
      )}
    </div>
  );
}
