import { useCallback, type KeyboardEvent } from "react";

import "./MirostatRockerSwitch.css";

/** Disque vertical : haut = 1 (I), milieu = 0 (O), bas = 2 (II). */
const POSITIONS = [
  { value: 1 as const, mark: "I", slot: "top" as const },
  { value: 0 as const, mark: "O", slot: "mid" as const },
  { value: 2 as const, mark: "II", slot: "bot" as const },
] as const;

const CYCLE: (0 | 1 | 2)[] = [1, 0, 2];

export function stepMirostatValue(
  current: number | null,
  direction: 1 | -1,
): 0 | 1 | 2 {
  if (current === null || !CYCLE.includes(current as 0 | 1 | 2)) {
    return direction > 0 ? 2 : 1;
  }
  const index = CYCLE.indexOf(current as 0 | 1 | 2);
  return CYCLE[(index + direction + CYCLE.length) % CYCLE.length];
}

export type MirostatRockerSwitchProps = {
  value: number | null;
  onChange: (value: number) => void;
  ariaLabel: string;
  disabled?: boolean;
};

function normalizeValue(value: number | null): 0 | 1 | 2 | null {
  if (value === 0 || value === 1 || value === 2) return value;
  return null;
}

const MirostatRockerSwitch = ({
  value,
  onChange,
  ariaLabel,
  disabled = false,
}: MirostatRockerSwitchProps) => {
  const active = normalizeValue(value);
  const activeSlot =
    active === null ? null : POSITIONS.find((p) => p.value === active)?.slot ?? null;

  const step = useCallback(
    (direction: 1 | -1) => {
      if (active === null) {
        onChange(direction > 0 ? 2 : 1);
        return;
      }
      const index = CYCLE.indexOf(active);
      onChange(CYCLE[(index + direction + CYCLE.length) % CYCLE.length]);
    },
    [active, onChange],
  );

  const onKeyDown = (event: KeyboardEvent) => {
    if (disabled) return;
    if (event.key === "ArrowUp") {
      event.preventDefault();
      step(-1);
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      step(1);
    }
  };

  const leverSlot = activeSlot ?? "mid";

  return (
    <div
      className={[
        "mirostat-rocker",
        disabled ? "mirostat-rocker--disabled" : "",
        active === null ? "mirostat-rocker--unset" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      role="radiogroup"
      aria-label={ariaLabel}
      tabIndex={disabled ? -1 : 0}
      onKeyDown={onKeyDown}
    >
      <div className="mirostat-rocker__scene" aria-hidden="true">
        <div className="mirostat-rocker__panel">
          <div className="mirostat-rocker__bezel" />
          <div className="mirostat-rocker__well">
            <div className="mirostat-rocker__pivot">
              <div className={`mirostat-rocker__lever mirostat-rocker__lever--${leverSlot}`}>
                <div className="mirostat-rocker__lever-face">
                  {POSITIONS.map((position) => {
                    const isActive = active === position.value;
                    return (
                      <button
                        key={position.slot}
                        type="button"
                        className={[
                          "mirostat-rocker__segment",
                          isActive ? "mirostat-rocker__segment--active" : "",
                        ]
                          .filter(Boolean)
                          .join(" ")}
                        role="radio"
                        aria-checked={isActive}
                        aria-label={`${position.mark}, ${position.value}`}
                        disabled={disabled}
                        onPointerDown={(e) => e.stopPropagation()}
                        onClick={(e) => {
                          e.stopPropagation();
                          onChange(position.value);
                        }}
                      >
                        <span className="mirostat-rocker__mark">{position.mark}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MirostatRockerSwitch;
