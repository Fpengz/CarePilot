export type ConsoleMethod = (message?: unknown, ...optionalParams: unknown[]) => void;

export interface ConsoleLike {
  info: ConsoleMethod;
  error: ConsoleMethod;
}

export function getConsolePrinter(consoleLike: ConsoleLike, event: string): ConsoleMethod {
  const method = event.includes("error") ? consoleLike.error : consoleLike.info;
  return method.bind(consoleLike);
}
