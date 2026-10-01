"use client";

import { useState } from "react";

import { FormField } from "@/components/ui/FormField";
import { SelectField } from "@/components/ui/SelectField";

import styles from "./RecurrenceFields.module.css";

const weekdays = ["L", "M", "X", "J", "V", "S", "D"];
const weekdayOptions = [
  "lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo",
].map((label, value) => ({ label, value: String(value) }));

export function RecurrenceFields({ disabled = false }: { disabled?: boolean }) {
  const now = new Date();
  const defaultWeekday = String((now.getDay() + 6) % 7);
  const defaultWeek = String(Math.min(5, Math.ceil(now.getDate() / 7)));
  const [preset, setPreset] = useState("NONE");
  const [unit, setUnit] = useState("DAY");
  const [monthlyMode, setMonthlyMode] = useState("DAY_OF_MONTH");
  const [ends, setEnds] = useState("NEVER");
  const monthly = preset === "MONTHLY" || (preset === "CUSTOM" && unit === "MONTH");
  const weekly = preset === "WEEKLY" || (preset === "CUSTOM" && unit === "WEEK");

  return (
    <fieldset className={styles.group} disabled={disabled}>
      <legend>Programación</legend>
      <SelectField label="Repetición" name="recurrencePreset" value={preset}
        onChange={(event) => setPreset(event.target.value)} options={[
          { value: "NONE", label: "No repetir" },
          { value: "WORKDAYS", label: "Todos los días laborables" },
          { value: "DAILY", label: "Cada día" },
          { value: "WEEKLY", label: "Cada semana" },
          { value: "MONTHLY", label: "Cada mes" },
          { value: "CUSTOM", label: "Personalizar…" },
        ]} />

      {preset === "CUSTOM" ? (
        <div className={styles.interval}>
          <FormField label="Repetir cada" name="repeatInterval" type="number" min={1} max={365}
            defaultValue="1" required />
          <SelectField label="Periodo" name="repeatUnit" value={unit}
            onChange={(event) => setUnit(event.target.value)} options={[
              { value: "DAY", label: "Día(s)" },
              { value: "WEEK", label: "Semana(s)" },
              { value: "MONTH", label: "Mes(es)" },
            ]} />
        </div>
      ) : null}

      {weekly ? (
        preset === "WEEKLY" ? (
          <SelectField label="Día de la semana" name="weekdays" defaultValue={defaultWeekday}
            options={weekdayOptions} />
        ) : (
          <div>
            <span className={styles.label}>Días</span>
            <div className={styles.weekdays}>
              {weekdays.map((label, index) => (
                <label key={label} className={styles.day}>
                  <input type="checkbox" name="weekdays" value={index}
                    defaultChecked={String(index) === defaultWeekday} />
                  <span>{label}</span>
                </label>
              ))}
            </div>
          </div>
        )
      ) : null}

      {monthly ? (
        <div className={styles.monthly}>
          <SelectField label="Repetir el" name="monthlyMode" value={monthlyMode}
            onChange={(event) => setMonthlyMode(event.target.value)} options={[
              { value: "DAY_OF_MONTH", label: "Día del mes" },
              { value: "NTH_WEEKDAY", label: "Posición y día" },
            ]} />
          {monthlyMode === "DAY_OF_MONTH" ? (
            <FormField label="Día" name="monthlyDay" type="number" min={1} max={31}
              defaultValue={String(now.getDate())} required />
          ) : (
            <div className={styles.interval}>
              <SelectField label="Semana" name="monthlyWeek" defaultValue={defaultWeek} options={[
                { value: "1", label: "Primera" }, { value: "2", label: "Segunda" },
                { value: "3", label: "Tercera" }, { value: "4", label: "Cuarta" },
                { value: "5", label: "Última" },
              ]} />
              <SelectField label="Día" name="monthlyWeekday" defaultValue={defaultWeekday}
                options={weekdayOptions} />
            </div>
          )}
        </div>
      ) : null}

      {preset !== "NONE" ? (
        <div className={styles.ends}>
          <span className={styles.label}>Termina</span>
          <label><input type="radio" name="recurrenceEnd" value="NEVER" checked={ends === "NEVER"}
            onChange={() => setEnds("NEVER")} /> Nunca</label>
          <label><input type="radio" name="recurrenceEnd" value="ON" checked={ends === "ON"}
            onChange={() => setEnds("ON")} /> El</label>
          <input aria-label="Fecha de finalización" type="date" name="recurrenceEndsOn"
            disabled={ends !== "ON"} required={ends === "ON"} />
        </div>
      ) : null}
    </fieldset>
  );
}
