
import {
    ContextMenu,
    ContextMenuCheckboxItem,
    ContextMenuContent,
    ContextMenuItem,
    ContextMenuSeparator,
    ContextMenuShortcut,
    ContextMenuSub,
    ContextMenuSubContent,
    ContextMenuSubTrigger,
    ContextMenuTrigger,
} from "@/components/ui/context-menu"

export type MenuItem = {
    label?: string;
    icon?: React.ReactNode;
    disabled?: boolean;
    separator?: boolean;
    subItems?: MenuItem[];
    checkbox?: boolean;
    checked?: boolean;
    shortcut?: string;
    onClick?: () => void;
};

type CustomContextMenuProps = {
    trigger: React.ReactNode;
    menuItems: MenuItem[];
};

export function CustomContextMenu({ trigger, menuItems }: CustomContextMenuProps) {
    return (
        <ContextMenu>
            <ContextMenuTrigger asChild>
                {trigger}
            </ContextMenuTrigger>
            <ContextMenuContent className="w-64">
                {menuItems.map((item, index) => {
                    if (item.separator) return <ContextMenuSeparator key={index} />;
                    if (item.subItems) {
                        return (
                            <ContextMenuSub key={index}>
                                <ContextMenuSubTrigger inset>
                                    {item.icon && <span className="mr-2">{item.icon}</span>}
                                    {item.label}
                                </ContextMenuSubTrigger>
                                <ContextMenuSubContent className="w-48">
                                    {item.subItems.map((subItem, subIndex) => (
                                        subItem.separator ? (
                                            <ContextMenuSeparator key={subIndex} />
                                        ) : (
                                            <ContextMenuItem key={subIndex} inset onClick={item.onClick}>
                                                {subItem.icon && <span className="mr-2">{subItem.icon}</span>}
                                                {subItem.label}
                                                {subItem.shortcut && (
                                                    <ContextMenuShortcut>{subItem.shortcut}</ContextMenuShortcut>
                                                )}
                                            </ContextMenuItem>
                                        )
                                    ))}
                                </ContextMenuSubContent>
                            </ContextMenuSub>
                        );
                    }
                    if (item.checkbox) {
                        return (
                            <ContextMenuCheckboxItem key={index} checked={item.checked} onClick={item.onClick}>
                                {item.icon && <span className="mr-2">{item.icon}</span>}
                                {item.label}
                                {item.shortcut && (
                                    <ContextMenuShortcut>{item.shortcut}</ContextMenuShortcut>
                                )}
                            </ContextMenuCheckboxItem>
                        );
                    }
                    return (
                        <ContextMenuItem key={index} inset disabled={item.disabled} onClick={item.onClick}>
                            {item.icon && <span className="mr-2">{item.icon}</span>}
                            {item.label}

                        </ContextMenuItem>
                    );
                })}
            </ContextMenuContent>
        </ContextMenu>
    );
}
