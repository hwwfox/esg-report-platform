export function hasPermission(permissions: string[], permission: string): boolean {
  return permissions.includes('*')
    || permissions.includes(permission)
    || permissions.some((item) => item.endsWith(':*') && permission.startsWith(item.slice(0, -1)));
}

export function hasAllPermissions(permissions: string[], requiredPermissions: string[]): boolean {
  return requiredPermissions.every((permission) => hasPermission(permissions, permission));
}
