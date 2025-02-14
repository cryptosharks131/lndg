import React from 'react';
import MultipleSelector, { Option } from '@/components/ui/multi-select'
const OPTIONS: Option[] = [
    { label: 'nextjs', value: 'nextjs' },
    { label: 'React', value: 'react' },
    { label: 'Remix', value: 'remix' },
    { label: 'Vite', value: 'vite' },
    { label: 'Nuxt', value: 'nuxt' },
    { label: 'Vue', value: 'vue' },
    { label: 'Svelte', value: 'svelte' },
    { label: 'Angular', value: 'angular' },
    { label: 'Ember', value: 'ember', disable: true },
    { label: 'Gatsby', value: 'gatsby', disable: true },
    { label: 'Astro', value: 'astro' },
];

const ChannelSelector = () => {
    return (
        <div className="w-full">
            <MultipleSelector
                defaultOptions={OPTIONS}
                placeholder="Select Channels"
                emptyIndicator={
                    <p className="text-center text-sm ">
                        no results found.
                    </p>
                }
            />
        </div>
    );
};

export default ChannelSelector;
