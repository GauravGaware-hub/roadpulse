import { useCallback, useEffect, useState } from "react";

// Lightweight hash router: works on any static host without rewrite rules.
export const ROUTES = ["overview", "map", "events", "hotspots", "upload", "analytics", "demo", "about", "settings"] as const;
export type Route = (typeof ROUTES)[number];

const parse = (): Route => {
  const h = window.location.hash.replace(/^#\/?/, "") as Route;
  return (ROUTES as readonly string[]).includes(h) ? h : "overview";
};

export function useRoute(): [Route, (r: Route) => void] {
  const [route, setRoute] = useState<Route>(parse);
  useEffect(() => {
    const on = () => {
      setRoute(parse());
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  const go = useCallback((r: Route) => {
    window.location.hash = `/${r}`;
  }, []);
  return [route, go];
}
