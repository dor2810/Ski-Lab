// Thin-stroke line icons, per the brand spec (~1.5-2px stroke, rounded
// caps). Semantic re-exports of lucide-react so callers don't need to
// know the underlying icon-library names, and swapping the library
// later only touches this one file.
import {
  Plane,
  BedDouble,
  Car,
  CableCar,
  Mountain,
  MountainSnow,
  Utensils,
  Calendar,
  Euro,
  Tag,
  Snowflake,
  TrendingUp,
  MapPin,
  ChartLine,
  ShieldCheck,
  CloudSnow,
  type LucideProps,
} from "lucide-react";

const defaultProps: Partial<LucideProps> = {
  strokeWidth: 1.75,
  absoluteStrokeWidth: false,
};

export const FlightIcon = (p: LucideProps) => <Plane {...defaultProps} {...p} />;
export const StayIcon = (p: LucideProps) => <BedDouble {...defaultProps} {...p} />;
export const TransferIcon = (p: LucideProps) => <Car {...defaultProps} {...p} />;
export const GondolaIcon = (p: LucideProps) => <CableCar {...defaultProps} {...p} />;
export const MountainIcon = (p: LucideProps) => <Mountain {...defaultProps} {...p} />;
export const SnowMountainIcon = (p: LucideProps) => <MountainSnow {...defaultProps} {...p} />;
export const FoodIcon = (p: LucideProps) => <Utensils {...defaultProps} {...p} />;
export const CalendarIcon = (p: LucideProps) => <Calendar {...defaultProps} {...p} />;
export const PriceIcon = (p: LucideProps) => <Euro {...defaultProps} {...p} />;
export const LiftPassIcon = (p: LucideProps) => <Tag {...defaultProps} {...p} />;
export const SnowIcon = (p: LucideProps) => <Snowflake {...defaultProps} {...p} />;
export const TrendIcon = (p: LucideProps) => <TrendingUp {...defaultProps} {...p} />;
export const PinIcon = (p: LucideProps) => <MapPin {...defaultProps} {...p} />;
export const ChartIcon = (p: LucideProps) => <ChartLine {...defaultProps} {...p} />;
export const ConfidenceIcon = (p: LucideProps) => <ShieldCheck {...defaultProps} {...p} />;
export const WeatherIcon = (p: LucideProps) => <CloudSnow {...defaultProps} {...p} />;
