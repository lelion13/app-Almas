import { useEffect, useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import {
  ApiError,
  getBackupConfig,
  getBackupLogs,
  getBackupStatus,
  runManualBackup,
  updateBackupConfig,
  type BackupConfig,
  type BackupLog,
  type BackupStatus,
} from "@/services/api";
import { useAuth } from "@/hooks/useAuth";

const WEEKDAYS = [
  { value: 0, label: "Lunes" },
  { value: 1, label: "Martes" },
  { value: 2, label: "Miércoles" },
  { value: 3, label: "Jueves" },
  { value: 4, label: "Viernes" },
  { value: 5, label: "Sábado" },
  { value: 6, label: "Domingo" },
];

function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined || bytes === 0) return "—";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr);
    return d.toLocaleString("es-AR", {
      dateStyle: "short",
      timeStyle: "medium",
    });
  } catch {
    return dateStr;
  }
}

export default function SettingsBackupPage() {
  const { me } = useAuth();

  const [config, setConfig] = useState<BackupConfig | null>(null);
  const [statusInfo, setStatusInfo] = useState<BackupStatus | null>(null);
  const [logs, setLogs] = useState<BackupLog[]>([]);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [runningManual, setRunningManual] = useState(false);

  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Form states
  const [enabled, setEnabled] = useState(false);
  const [scheduleType, setScheduleType] = useState("daily");
  const [scheduleTime, setScheduleTime] = useState("03:00");
  const [scheduleDayOfWeek, setScheduleDayOfWeek] = useState(0);
  const [s3EndpointUrl, setS3EndpointUrl] = useState("");
  const [s3BucketName, setS3BucketName] = useState("");
  const [s3RegionName, setS3RegionName] = useState("auto");
  const [s3AccessKeyId, setS3AccessKeyId] = useState("");
  const [s3SecretAccessKey, setS3SecretAccessKey] = useState("");
  const [s3Prefix, setS3Prefix] = useState("almas-backups/");
  const [retentionCount, setRetentionCount] = useState(15);

  async function loadData() {
    setErrorMsg(null);
    try {
      const [cfg, stat, logList] = await Promise.all([
        getBackupConfig(),
        getBackupStatus(),
        getBackupLogs(50),
      ]);
      setConfig(cfg);
      setStatusInfo(stat);
      setLogs(logList);

      // Populate form
      setEnabled(cfg.enabled);
      setScheduleType(cfg.schedule_type || "daily");
      setScheduleTime(cfg.schedule_time || "03:00");
      setScheduleDayOfWeek(cfg.schedule_day_of_week ?? 0);
      setS3EndpointUrl(cfg.s3_endpoint_url || "");
      setS3BucketName(cfg.s3_bucket_name || "");
      setS3RegionName(cfg.s3_region_name || "auto");
      setS3AccessKeyId(cfg.s3_access_key_id || "");
      setS3SecretAccessKey("");
      setS3Prefix(cfg.s3_prefix || "almas-backups/");
      setRetentionCount(cfg.retention_count || 15);
    } catch (e) {
      setErrorMsg(e instanceof ApiError ? e.message : "Error al cargar configuración de backups.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  if (me?.role !== "admin") {
    return <Navigate to="/" replace />;
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);
    setSaving(true);
    try {
      const updated = await updateBackupConfig({
        enabled,
        schedule_type: scheduleType,
        schedule_time: scheduleTime,
        schedule_day_of_week: scheduleType === "weekly" ? scheduleDayOfWeek : null,
        s3_endpoint_url: s3EndpointUrl.trim() || null,
        s3_bucket_name: s3BucketName.trim(),
        s3_region_name: s3RegionName.trim() || "auto",
        s3_access_key_id: s3AccessKeyId.trim(),
        s3_secret_access_key: s3SecretAccessKey.trim() || undefined,
        s3_prefix: s3Prefix.trim() || "almas-backups/",
        retention_count: Number(retentionCount) || 15,
      });
      setConfig(updated);
      setS3SecretAccessKey("");
      setSuccessMsg("Configuración de backups guardada exitosamente.");
      const stat = await getBackupStatus();
      setStatusInfo(stat);
    } catch (e) {
      setErrorMsg(e instanceof ApiError ? e.message : "Error al guardar la configuración.");
    } finally {
      setSaving(false);
    }
  }

  async function handleTriggerManual() {
    if (runningManual) return;
    setErrorMsg(null);
    setSuccessMsg(null);
    setRunningManual(true);
    try {
      const res = await runManualBackup();
      if (res.success) {
        setSuccessMsg(res.message);
      } else {
        setErrorMsg(res.message);
      }
      const [stat, logList] = await Promise.all([getBackupStatus(), getBackupLogs(50)]);
      setStatusInfo(stat);
      setLogs(logList);
    } catch (e) {
      setErrorMsg(e instanceof ApiError ? e.message : "Error al ejecutar el backup manual.");
    } finally {
      setRunningManual(false);
    }
  }

  if (loading) {
    return (
      <div className="p-6 text-slate-600 flex items-center justify-center">
        Cargando configuración…
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Configuración del Sistema</h1>
          <p className="text-sm text-slate-500">
            Gestión de copias de seguridad de la base de datos y almacenamiento externo S3.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => void loadData()}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 shadow-sm"
          >
            Actualizar
          </button>
          <button
            type="button"
            onClick={() => void handleTriggerManual()}
            disabled={runningManual || statusInfo?.is_running}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50 flex items-center gap-2"
          >
            {runningManual || statusInfo?.is_running ? (
              <>
                <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span>Generando backup…</span>
              </>
            ) : (
              <span>Realizar backup ahora</span>
            )}
          </button>
        </div>
      </div>

      {successMsg && (
        <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-4 text-sm text-emerald-800 flex items-center justify-between">
          <span>{successMsg}</span>
          <button type="button" onClick={() => setSuccessMsg(null)} className="text-emerald-600 hover:text-emerald-900 font-bold ml-4">
            ✕
          </button>
        </div>
      )}

      {errorMsg && (
        <div className="rounded-lg bg-rose-50 border border-rose-200 p-4 text-sm text-rose-800 flex items-center justify-between">
          <span>{errorMsg}</span>
          <button type="button" onClick={() => setErrorMsg(null)} className="text-rose-600 hover:text-rose-900 font-bold ml-4">
            ✕
          </button>
        </div>
      )}

      {/* Status Highlights */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs font-semibold text-slate-400 uppercase">Estado del Scheduler</div>
          <div className="mt-1 flex items-center gap-2">
            <span
              className={`inline-block h-3 w-3 rounded-full ${
                config?.enabled ? "bg-emerald-500" : "bg-slate-300"
              }`}
            />
            <span className="font-medium text-slate-800">
              {config?.enabled ? "Activo (Programado)" : "Desactivado"}
            </span>
          </div>
          {config?.enabled && statusInfo?.next_run_at && (
            <p className="mt-2 text-xs text-slate-500">
              Próxima ejecución: <span className="font-semibold text-slate-700">{formatDate(statusInfo.next_run_at)}</span>
            </p>
          )}
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs font-semibold text-slate-400 uppercase">Último Backup</div>
          <div className="mt-1 font-medium text-slate-800 flex items-center gap-2">
            {statusInfo?.last_log ? (
              <>
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                    statusInfo.last_log.status === "success"
                      ? "bg-emerald-100 text-emerald-800"
                      : statusInfo.last_log.status === "running"
                      ? "bg-amber-100 text-amber-800"
                      : "bg-rose-100 text-rose-800"
                  }`}
                >
                  {statusInfo.last_log.status === "success"
                    ? "Exitoso"
                    : statusInfo.last_log.status === "running"
                    ? "En progreso"
                    : "Fallido"}
                </span>
                <span className="text-sm text-slate-600">{formatDate(statusInfo.last_log.started_at)}</span>
              </>
            ) : (
              <span className="text-sm text-slate-400">Sin registros</span>
            )}
          </div>
          {statusInfo?.last_log?.file_size_bytes ? (
            <p className="mt-2 text-xs text-slate-500">
              Tamaño: <span className="font-semibold text-slate-700">{formatBytes(statusInfo.last_log.file_size_bytes)}</span> (duración: {statusInfo.last_log.duration_seconds ?? "—"}s)
            </p>
          ) : null}
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs font-semibold text-slate-400 uppercase">Destino S3 / Bucket</div>
          <div className="mt-1 font-medium text-slate-800 truncate" title={config?.s3_bucket_name || "No configurado"}>
            {config?.s3_bucket_name ? config.s3_bucket_name : <span className="text-slate-400 italic">No configurado</span>}
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Retención: <span className="font-semibold text-slate-700">{config?.retention_count ?? 15} copias</span>
          </p>
        </div>
      </div>

      {/* Configuration Form */}
      <form onSubmit={(e) => void handleSave(e)} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-6">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Parámetros de Configuración</h2>
          <p className="text-xs text-slate-500 mt-1">
            Configura las credenciales de tu proveedor de almacenamiento S3 (Cloudflare R2, AWS S3, MinIO) y la frecuencia del cron.
          </p>
        </div>

        {/* Section: Scheduler */}
        <div className="border-t border-slate-100 pt-4 space-y-4">
          <h3 className="text-sm font-semibold text-slate-800">1. Programación Automática (Cron)</h3>
          
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enabled"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
            />
            <label htmlFor="enabled" className="text-sm font-medium text-slate-700 cursor-pointer">
              Habilitar backup automático periódico en segundo plano
            </label>
          </div>

          <div className={`grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 ${!enabled ? "opacity-60 pointer-events-none" : ""}`}>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Frecuencia</label>
              <select
                value={scheduleType}
                onChange={(e) => setScheduleType(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                <option value="daily">Diario</option>
                <option value="weekly">Semanal</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Hora de ejecución (24h)</label>
              <input
                type="time"
                value={scheduleTime}
                onChange={(e) => setScheduleTime(e.target.value)}
                required
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            {scheduleType === "weekly" && (
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Día de la semana</label>
                <select
                  value={scheduleDayOfWeek}
                  onChange={(e) => setScheduleDayOfWeek(Number(e.target.value))}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  {WEEKDAYS.map((w) => (
                    <option key={w.value} value={w.value}>
                      {w.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>

        {/* Section: S3 Credentials */}
        <div className="border-t border-slate-100 pt-4 space-y-4">
          <h3 className="text-sm font-semibold text-slate-800">2. Destino de Almacenamiento S3 Compatible</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Endpoint URL (opcional para Cloudflare R2 / MinIO / Backblaze)
              </label>
              <input
                type="url"
                value={s3EndpointUrl}
                onChange={(e) => setS3EndpointUrl(e.target.value)}
                placeholder="https://<account_id>.r2.cloudflarestorage.com"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 font-mono"
              />
              <span className="text-[11px] text-slate-400">
                Dejar en blanco si se utiliza AWS S3 estándar.
              </span>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Nombre del Bucket *</label>
              <input
                type="text"
                value={s3BucketName}
                onChange={(e) => setS3BucketName(e.target.value)}
                placeholder="almas-backups"
                required
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Región</label>
              <input
                type="text"
                value={s3RegionName}
                onChange={(e) => setS3RegionName(e.target.value)}
                placeholder="auto"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Access Key ID *</label>
              <input
                type="text"
                value={s3AccessKeyId}
                onChange={(e) => setS3AccessKeyId(e.target.value)}
                placeholder="AKIA..."
                required
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Secret Access Key {config?.has_secret_access_key && <span className="text-emerald-600 font-normal">(Ya guardado)</span>}
              </label>
              <input
                type="password"
                value={s3SecretAccessKey}
                onChange={(e) => setS3SecretAccessKey(e.target.value)}
                placeholder={config?.has_secret_access_key ? "•••••••••••••••• (dejar vacío para mantener)" : "Secret key..."}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Prefijo / Carpeta en Bucket</label>
              <input
                type="text"
                value={s3Prefix}
                onChange={(e) => setS3Prefix(e.target.value)}
                placeholder="almas-backups/"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Retención (cantidad máxima de backups a conservar)</label>
              <input
                type="number"
                min="1"
                max="365"
                value={retentionCount}
                onChange={(e) => setRetentionCount(Number(e.target.value))}
                required
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              <span className="text-[11px] text-slate-400">
                Los backups más antiguos que excedan este número se eliminarán automáticamente de S3.
              </span>
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-4 border-t border-slate-100">
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white shadow hover:bg-brand-700 disabled:opacity-50"
          >
            {saving ? "Guardando…" : "Guardar Configuración"}
          </button>
        </div>
      </form>

      {/* Backup History Logs */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Historial de Ejecuciones</h2>
            <p className="text-xs text-slate-500">Últimos 50 eventos de backup generados</p>
          </div>
        </div>

        {logs.length === 0 ? (
          <div className="py-8 text-center text-sm text-slate-400">
            Aún no se han ejecutado backups.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-slate-500 uppercase text-[10px] tracking-wider border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Fecha / Hora</th>
                  <th className="py-2.5 px-3">Tipo</th>
                  <th className="py-2.5 px-3">Estado</th>
                  <th className="py-2.5 px-3">Archivo</th>
                  <th className="py-2.5 px-3">Tamaño</th>
                  <th className="py-2.5 px-3">Duración</th>
                  <th className="py-2.5 px-3">Clave S3 / Error</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/50">
                    <td className="py-2.5 px-3 whitespace-nowrap font-medium text-slate-700">
                      {formatDate(log.started_at)}
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <span className="capitalize">{log.trigger_type === "scheduled" ? "Programado" : "Manual"}</span>
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold ${
                          log.status === "success"
                            ? "bg-emerald-100 text-emerald-800"
                            : log.status === "running"
                            ? "bg-amber-100 text-amber-800"
                            : "bg-rose-100 text-rose-800"
                        }`}
                      >
                        {log.status === "success"
                          ? "Exitoso"
                          : log.status === "running"
                          ? "En progreso"
                          : "Falló"}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-800 truncate max-w-[180px]" title={log.file_name}>
                      {log.file_name}
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap font-mono">
                      {formatBytes(log.file_size_bytes)}
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      {log.duration_seconds !== null ? `${log.duration_seconds}s` : "—"}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] truncate max-w-[260px]">
                      {log.status === "failed" ? (
                        <span className="text-rose-600 font-sans" title={log.error_message || ""}>
                          {log.error_message}
                        </span>
                      ) : (
                        <span className="text-slate-500" title={log.storage_key || ""}>
                          {log.storage_key || "—"}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
