import { Result } from 'antd';

export function ForbiddenPage() {
  return <Result status="403" title="无权限" subTitle="当前账号无权访问该资源，请联系管理员。" />;
}
