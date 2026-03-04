/**
 * Application shell layout — sidebar navigation, header, and theme toggle.
 *
 * Responsive behaviour:
 * - **Desktop** (≥ 768px): persistent sidebar with collapse/expand toggle button
 * - **Mobile** (< 768px): sidebar hidden by default, hamburger button opens a Drawer overlay
 *
 * @module AppLayout
 */
import { useState, useEffect, useCallback } from 'react';
import { Layout, Menu, Switch, Space, Button, Drawer, Grid, theme } from 'antd';
import {
    DashboardOutlined,
    UploadOutlined,
    SunOutlined,
    MoonOutlined,
    MenuFoldOutlined,
    MenuUnfoldOutlined,
    MenuOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router';
import { useTheme } from '../../contexts/ThemeContext';

const { Sider, Content, Header } = Layout;
const { useBreakpoint } = Grid;

/** Navigation menu items. */
const MENU_ITEMS = [
    { key: '/', icon: <DashboardOutlined />, label: 'Dashboard' },
    { key: '/upload', icon: <UploadOutlined />, label: 'Upload Logs' },
];

/**
 * Application shell layout with sidebar navigation and dark mode toggle.
 *
 * - Desktop: collapsible sidebar with a smooth collapse/expand button
 * - Mobile: hamburger menu in header opens a Drawer with navigation
 * - Theme-aware: uses Ant Design tokens for automatic dark mode support
 */
export function AppLayout() {
    const navigate = useNavigate();
    const location = useLocation();
    const { isDark, toggleTheme } = useTheme();
    const { token } = theme.useToken();
    const screens = useBreakpoint();

    const isMobile = !screens.md;

    const [collapsed, setCollapsed] = useState(false);
    const [drawerOpen, setDrawerOpen] = useState(false);

    /** Close drawer on route change (mobile). */
    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect -- syncing UI with router state
        setDrawerOpen(false);
    }, [location.pathname]);

    /** Handle menu click — navigate and close drawer if mobile. */
    const handleMenuClick = useCallback(
        ({ key }: { key: string }) => {
            navigate(key);
            if (isMobile) setDrawerOpen(false);
        },
        [navigate, isMobile],
    );

    /* ─── Logo component ──────────────────────────────────── */
    const logo = (showFull: boolean) => (
        <div
            style={{
                height: 64,
                display: 'flex',
                alignItems: 'center',
                justifyContent: showFull ? 'flex-start' : 'center',
                paddingLeft: showFull ? 20 : 0,
                gap: 10,
                fontWeight: 700,
                fontSize: 18,
                color: token.colorPrimary,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                transition: 'all 0.2s',
                borderBottom: `1px solid ${token.colorBorderSecondary}`,
            }}
        >
            <img
                src="/logo.png"
                alt="LOG Analyzer"
                style={{
                    width: showFull ? 32 : 24,
                    height: showFull ? 32 : 24,
                    transition: 'all 0.2s',
                }}
            />
            {showFull && <span>LOG Analyzer</span>}
        </div>
    );

    /* ─── Menu component ──────────────────────────────────── */
    const menuContent = (
        <Menu
            mode="inline"
            theme={isDark ? 'dark' : 'light'}
            selectedKeys={[location.pathname]}
            items={MENU_ITEMS}
            onClick={handleMenuClick}
            style={{ borderInlineEnd: 'none' }}
        />
    );

    /* ─── Theme toggle ────────────────────────────────────── */
    const themeToggle = (
        <Space size={4}>
            <SunOutlined
                style={{ color: isDark ? token.colorTextQuaternary : '#faad14', fontSize: 16 }}
            />
            <Switch checked={isDark} onChange={toggleTheme} size="small" />
            <MoonOutlined
                style={{ color: isDark ? token.colorPrimary : token.colorTextQuaternary, fontSize: 16 }}
            />
        </Space>
    );

    return (
        <Layout style={{ minHeight: '100vh' }}>
            {/* ── Desktop sidebar ────────────────────────── */}
            {!isMobile && (
                <Sider
                    collapsible
                    collapsed={collapsed}
                    onCollapse={setCollapsed}
                    trigger={null}
                    width={220}
                    collapsedWidth={64}
                    theme={isDark ? 'dark' : 'light'}
                    style={{
                        borderRight: `1px solid ${token.colorBorderSecondary}`,
                        position: 'sticky',
                        top: 0,
                        left: 0,
                        height: '100vh',
                        overflow: 'auto',
                    }}
                >
                    {logo(!collapsed)}
                    {menuContent}
                </Sider>
            )}

            {/* ── Mobile drawer ──────────────────────────── */}
            {isMobile && (
                <Drawer
                    placement="left"
                    open={drawerOpen}
                    onClose={() => setDrawerOpen(false)}
                    width={260}
                    styles={{
                        body: { padding: 0 },
                        header: { display: 'none' },
                    }}
                >
                    {logo(true)}
                    {menuContent}
                </Drawer>
            )}

            <Layout>
                <Header
                    style={{
                        background: token.colorBgContainer,
                        padding: isMobile ? '0 12px' : '0 24px',
                        borderBottom: `1px solid ${token.colorBorderSecondary}`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        position: 'sticky',
                        top: 0,
                        zIndex: 10,
                        height: 64,
                    }}
                >
                    <Space>
                        {/* Collapse / Hamburger toggle */}
                        <Button
                            type="text"
                            icon={
                                isMobile
                                    ? <MenuOutlined />
                                    : collapsed
                                        ? <MenuUnfoldOutlined />
                                        : <MenuFoldOutlined />
                            }
                            onClick={() =>
                                isMobile
                                    ? setDrawerOpen(true)
                                    : setCollapsed((c) => !c)
                            }
                            style={{ fontSize: 18, width: 48, height: 48 }}
                        />
                        <span
                            style={{
                                fontWeight: 600,
                                fontSize: isMobile ? 14 : 16,
                                color: token.colorText,
                                whiteSpace: 'nowrap',
                            }}
                        >
                            Nginx Log Analyzer
                        </span>
                    </Space>

                    {themeToggle}
                </Header>

                <Content
                    style={{
                        margin: isMobile ? 8 : 24,
                        padding: isMobile ? 12 : 24,
                        background: token.colorBgContainer,
                        borderRadius: token.borderRadiusLG,
                        minHeight: 360,
                    }}
                >
                    <Outlet />
                </Content>
            </Layout>
        </Layout>
    );
}
