import { ROUTE_KEY_MAP } from '@/constants/routeKeyMap';

const toRouteI18nKey = (routeName: string) => routeName
    .replace(/([A-Z]+)([A-Z][a-z])/g, '$1_$2')
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .replace(/[-\s]+/g, '_')
    .toLowerCase();

const getBreadcrumbLabel = (routeName: string) => {
    // Safety check
    if (!routeName) return '';
    const key = ROUTE_KEY_MAP[routeName] || toRouteI18nKey(routeName);
    const fullKey = `menu.${key}`;
    return fullKey;
};

export { getBreadcrumbLabel };
