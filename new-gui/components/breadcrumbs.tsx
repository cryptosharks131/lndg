"use client";
import Link from "next/link";
import {
    Breadcrumb,
    BreadcrumbItem,
    BreadcrumbLink,
    BreadcrumbList,
    BreadcrumbPage,
    BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { usePathname } from "next/navigation";
import { Fragment } from "react";

interface Breadcrumb {
    label: string;
    href: string;
    active?: boolean;
}

const parsePath = (path: string) => {
    // Remove leading and trailing slashes
    const cleanedPath = path.replace(/^\/+|\/+$/g, "");

    // Split the path into segments
    const segments = cleanedPath.split("/");

    // Create an array to hold the path objects
    const paths = segments.map((segment, index) => {
        // Construct the href by joining segments up to the current index
        const href = `/${segments.slice(0, index + 1).join("/")}`;
        // Capitalize the label
        const label = segment.charAt(0).toUpperCase() + segment.slice(1);
        return { label, href };
    });

    // Ensure the last item has the correct href (no trailing slash)
    if (paths.length > 0) {
        paths[paths.length - 1].href = paths[paths.length - 1].href.replace(
            /\/$/,
            ""
        );
    }

    return paths;
};

export default function Breadcrumbs() {
    const pathname = usePathname();
    const breadcrumbs: Breadcrumb[] = parsePath(pathname);
    // console.log(breadcrumbs);
    return (
        <Breadcrumb className="hidden md:flex">
            <BreadcrumbList>
                {breadcrumbs.map((breadcrumb, index) => (
                    <Fragment key={breadcrumb.href}>
                        <BreadcrumbItem>
                            {index == breadcrumbs.length - 1 ? (
                                <BreadcrumbPage>{breadcrumb.label}</BreadcrumbPage>
                            ) : (
                                <BreadcrumbLink asChild>
                                    <Link href={breadcrumb.href}>{breadcrumb.label}</Link>
                                </BreadcrumbLink>
                            )}
                        </BreadcrumbItem>
                        {index < breadcrumbs.length - 1 ? <BreadcrumbSeparator /> : null}
                    </Fragment>
                ))}
            </BreadcrumbList>
        </Breadcrumb>
    );
}