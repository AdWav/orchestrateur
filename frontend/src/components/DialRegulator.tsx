import {
  useCallback,
  useEffect,
  useRef,
  type CSSProperties,
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
} from "react";

import {
  angleToValue,
  clamp,
  digitalGaugeColor,
  formatDialValue,
  ratio,
  rotaryAmberColor,
  valueToLitCount,
  type DialRegulatorSize,
  type DialRegulatorVariant,
} from "./dialRegulatorUtils";

import "./DialRegulator.css";

export type DialRegulatorProps = {
  variant?: DialRegulatorVariant;
  value: number;
  min?: number;
  max?: number;
  onChange?: (value: number) => void;
  size?: DialRegulatorSize;
  segmentCount?: number;
  disabled?: boolean;
  /** Libellé accessible (sinon valeur + unité implicite). */
  ariaLabel?: string;
  /** Texte au centre (variante digital) à la place de la valeur numérique. */
  valueLabel?: string;
  /** Contenu interactif au centre (prioritaire sur valueLabel). */
  valueContent?: ReactNode;
  /** Pas de réglage à la molette au survol (désactive le scroll de la page). */
  wheelStep?: number;
  className?: string;
};

const DEFAULT_SEGMENTS: Record<DialRegulatorVariant, number> = {
  digital: 60,
  rotary: 48,
};

type TickRingProps = {
  variant: DialRegulatorVariant;
  litCount: number;
  segmentCount: number;
  accentColor: string;
  showMajorTicks?: boolean;
};

function TickRing({
  variant,
  litCount,
  segmentCount,
  accentColor,
  showMajorTicks = false,
}: TickRingProps) {
  const cx = 50;
  const cy = 50;
  const isDigital = variant === "digital";
  const outerR = isDigital ? 42 : 40;
  const tickLen = isDigital ? 5.5 : 4.2;
  const tickW = isDigital ? 2.2 : 2.8;
  const startAngle = 90;

  const ticks = Array.from({ length: segmentCount }, (_, i) => {
    const angle = startAngle + (i * 360) / segmentCount;
    const lit = i < litCount;
    const tickLevel = (i + 0.5) / segmentCount;
    const tickColor =
      lit && isDigital ? digitalGaugeColor(tickLevel) : lit ? accentColor : undefined;
    return (
      <g key={i} transform={`rotate(${angle} ${cx} ${cy})`}>
        <rect
          x={cx - tickW / 2}
          y={cy - outerR - tickLen}
          width={tickW}
          height={tickLen}
          rx={0.6}
          className={lit ? "dial-regulator__tick--lit" : "dial-regulator__tick--off"}
          fill={tickColor}
        />
      </g>
    );
  });

  const majorTicks =
    showMajorTicks &&
    Array.from({ length: 8 }, (_, i) => {
      const a = ((i * 45 - 90) * Math.PI) / 180;
      const inner = 44;
      const outer = 48;
      return (
        <line
          key={`major-${i}`}
          className="dial-regulator__major-tick"
          x1={cx + inner * Math.cos(a)}
          y1={cy + inner * Math.sin(a)}
          x2={cx + outer * Math.cos(a)}
          y2={cy + outer * Math.sin(a)}
        />
      );
    });

  return (
    <svg
      className="dial-regulator__svg"
      viewBox="0 0 100 100"
      aria-hidden="true"
    >
      {majorTicks}
      <g style={{ ["--dial-accent" as string]: accentColor }}>{ticks}</g>
    </svg>
  );
}

function pointerAngle(clientX: number, clientY: number, rect: DOMRect): number {
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height / 2;
  const rad = Math.atan2(clientY - cy, clientX - cx);
  return ((rad * 180) / Math.PI + 90 + 360) % 360;
}

const DialRegulator = ({
  variant = "digital",
  value,
  min = 0,
  max = 60,
  onChange,
  size = "md",
  segmentCount,
  disabled = false,
  ariaLabel,
  valueLabel,
  valueContent,
  wheelStep,
  className = "",
}: DialRegulatorProps) => {
  const rootRef = useRef<HTMLDivElement>(null);
  const safeValue = clamp(value, min, max);
  const t = ratio(safeValue, min, max);
  const segments = segmentCount ?? DEFAULT_SEGMENTS[variant];
  const litCount = valueToLitCount(safeValue, min, max, segments);
  const interactive = Boolean(onChange) && !disabled;
  const wheelEnabled = interactive && wheelStep !== undefined && wheelStep > 0;
  const accent =
    variant === "digital" ? digitalGaugeColor(t) : rotaryAmberColor(t);

  useEffect(() => {
    if (!wheelEnabled || !onChange) {
      return;
    }
    const node = rootRef.current;
    if (!node) {
      return;
    }
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      event.stopPropagation();
      const direction = event.deltaY < 0 ? 1 : -1;
      onChange(clamp(safeValue + direction * wheelStep, min, max));
    };
    node.addEventListener("wheel", onWheel, { passive: false });
    return () => node.removeEventListener("wheel", onWheel);
  }, [wheelEnabled, max, min, onChange, safeValue, wheelStep]);

  const emitValue = useCallback(
    (clientX: number, clientY: number) => {
      if (!onChange || !rootRef.current) return;
      const rect = rootRef.current.getBoundingClientRect();
      const angle = pointerAngle(clientX, clientY, rect);
      onChange(angleToValue(angle, min, max));
    },
    [max, min, onChange],
  );

  const onPointerDown = (event: PointerEvent) => {
    if (!interactive) return;
    event.preventDefault();
    rootRef.current?.setPointerCapture(event.pointerId);
    emitValue(event.clientX, event.clientY);
  };

  const onPointerMove = (event: PointerEvent) => {
    if (!interactive || !rootRef.current?.hasPointerCapture(event.pointerId)) {
      return;
    }
    emitValue(event.clientX, event.clientY);
  };

  const onPointerUp = (event: PointerEvent) => {
    rootRef.current?.releasePointerCapture(event.pointerId);
  };

  const onKeyDown = (event: KeyboardEvent) => {
    if (!onChange || disabled) return;
    const step = max <= 20 ? 1 : Math.max(1, Math.round((max - min) / 20));
    if (event.key === "ArrowRight" || event.key === "ArrowUp") {
      event.preventDefault();
      onChange(clamp(safeValue + step, min, max));
    } else if (event.key === "ArrowLeft" || event.key === "ArrowDown") {
      event.preventDefault();
      onChange(clamp(safeValue - step, min, max));
    }
  };

  const sizeClass = `dial-regulator--${size}`;
  const variantClass = `dial-regulator--${variant}`;
  const stateClasses = [
    "dial-regulator",
    variantClass,
    sizeClass,
    interactive ? "dial-regulator--interactive" : "",
    wheelEnabled ? "dial-regulator--wheel" : "",
    disabled ? "dial-regulator--disabled" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  const sliderLabel =
    ariaLabel ?? `Régulateur ${variant}, valeur ${safeValue} sur ${max}`;

  const commonProps = {
    ref: rootRef,
    className: stateClasses,
    style: { ["--dial-accent" as string]: accent } as CSSProperties,
    role: "slider" as const,
    tabIndex: interactive ? 0 : -1,
    "aria-valuemin": min,
    "aria-valuemax": max,
    "aria-valuenow": safeValue,
    "aria-label": sliderLabel,
    "aria-disabled": disabled || undefined,
    onPointerDown,
    onPointerMove,
    onPointerUp,
    onPointerCancel: onPointerUp,
    onKeyDown,
  };

  if (variant === "rotary") {
    return (
      <div {...commonProps}>
        <div className="dial-regulator__panel">
          <TickRing
            variant="rotary"
            litCount={litCount}
            segmentCount={segments}
            accentColor={accent}
            showMajorTicks
          />
          <button
            type="button"
            className="dial-regulator__knob"
            tabIndex={-1}
            aria-hidden="true"
          />
        </div>
      </div>
    );
  }

  return (
    <div {...commonProps}>
      <div className="dial-regulator__bezel">
        <div className="dial-regulator__face">
          <TickRing
            variant="digital"
            litCount={litCount}
            segmentCount={segments}
            accentColor={accent}
          />
          {valueContent ? (
            <div className="dial-regulator__value dial-regulator__value--slot">
              {valueContent}
            </div>
          ) : (
            <span className="dial-regulator__value" aria-hidden="true">
              {valueLabel ?? formatDialValue(safeValue, max)}
            </span>
          )}
          <div className="dial-regulator__glass" />
        </div>
      </div>
    </div>
  );
};

/** Galerie des variantes (démo / Storybook local). */
export function DialRegulatorShowcase() {
  return (
    <div className="dial-regulator-showcase">
      <section className="dial-regulator-showcase__section">
        <h3 className="dial-regulator-showcase__title">Jauge digitale</h3>
        <div className="dial-regulator-showcase__row">
          <div className="dial-regulator-showcase__item">
            <DialRegulator variant="digital" size="lg" value={60} max={60} />
            <span className="dial-regulator-showcase__caption">60</span>
          </div>
          <div className="dial-regulator-showcase__item">
            <DialRegulator variant="digital" size="sm" value={45} max={60} />
            <span className="dial-regulator-showcase__caption">45</span>
          </div>
          <div className="dial-regulator-showcase__item">
            <DialRegulator variant="digital" size="sm" value={30} max={60} />
            <span className="dial-regulator-showcase__caption">30</span>
          </div>
          <div className="dial-regulator-showcase__item">
            <DialRegulator variant="digital" size="sm" value={15} max={60} />
            <span className="dial-regulator-showcase__caption">15</span>
          </div>
        </div>
      </section>

      <section className="dial-regulator-showcase__section">
        <h3 className="dial-regulator-showcase__title">Bouton rotatif</h3>
        <div className="dial-regulator-showcase__row">
          <DialRegulator variant="rotary" size="lg" value={42} max={50} />
          <DialRegulator variant="rotary" size="md" value={28} max={50} />
          <DialRegulator variant="rotary" size="sm" value={12} max={50} />
        </div>
      </section>
    </div>
  );
}

export default DialRegulator;
