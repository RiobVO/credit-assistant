import { APP_MODE, type AppMode } from "./config";

// Хук вместо прямого импорта `APP_MODE` — при будущем переходе на runtime
// config / React context call-site не меняется.
export function useAppMode(): AppMode {
  return APP_MODE;
}
