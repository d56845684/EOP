import { ROUTE_KEY_MAP } from '@/constants/routeKeyMap';

const getBreadcrumbLabel = (routeName: string) => {
    // Safety check
    if (!routeName) return '';
    const key = ROUTE_KEY_MAP[routeName] || routeName.toLowerCase();
    const fullKey = `menu.${key}`;
    return fullKey;
};

export { getBreadcrumbLabel };