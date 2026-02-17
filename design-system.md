# Shared Design System — shadcn/ui

**Library:** [shadcn/ui](https://ui.shadcn.com)
**Foundation:** Radix UI primitives + Tailwind CSS
**Icons:** [Lucide React](https://lucide.dev)
**Charts:** [Recharts](https://recharts.org)
**Forms:** React Hook Form + Zod (or TanStack Form + Zod)
**Tables:** TanStack Table (for advanced data tables)
**Toasts:** Sonner
**Drawer:** Vaul
**Carousel:** Embla Carousel

> **Rule: All generated UI code MUST use only shadcn/ui components listed below.**
> Do not introduce any other component library. If a UI element is not covered here, compose it from these primitives.

---

## Installation

Components are added individually:
```bash
pnpm dlx shadcn@latest add <component-name>
```

All components import from `@/components/ui/<component>`.

---

## Typography

No dedicated typography component — use Tailwind utility classes:

| Style | Classes |
|-------|---------|
| H1 | `scroll-m-20 text-4xl font-extrabold tracking-tight` |
| H2 | `scroll-m-20 border-b pb-2 text-3xl font-semibold tracking-tight` |
| H3 | `scroll-m-20 text-2xl font-semibold tracking-tight` |
| H4 | `scroll-m-20 text-xl font-semibold tracking-tight` |
| Paragraph | `leading-7 [&:not(:first-child)]:mt-6` |
| Lead | `text-xl text-muted-foreground` |
| Large | `text-lg font-semibold` |
| Small | `text-sm font-medium leading-none` |
| Muted | `text-sm text-muted-foreground` |
| Blockquote | `mt-6 border-l-2 pl-6 italic` |
| Inline Code | `relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-sm font-semibold` |
| List | `my-6 ml-6 list-disc [&>li]:mt-2` |

---

## Components Reference

### 1. Accordion

Vertically stacked collapsible sections.

```tsx
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
```

| Prop (Accordion) | Values |
|------------------|--------|
| `type` | `"single"` / `"multiple"` |
| `collapsible` | `boolean` (when type="single") |
| `defaultValue` | `string` |

```tsx
<Accordion type="single" collapsible defaultValue="item-1">
  <AccordionItem value="item-1">
    <AccordionTrigger>Section Title</AccordionTrigger>
    <AccordionContent>Content here</AccordionContent>
  </AccordionItem>
</Accordion>
```

---

### 2. Alert

Callout for user attention.

```tsx
import { Alert, AlertDescription, AlertTitle, AlertAction } from "@/components/ui/alert"
```

| Prop | Values |
|------|--------|
| `variant` | `"default"` / `"destructive"` |

```tsx
<Alert variant="destructive">
  <AlertTitle>Error</AlertTitle>
  <AlertDescription>Something went wrong.</AlertDescription>
  <AlertAction><Button variant="outline" size="sm">Retry</Button></AlertAction>
</Alert>
```

---

### 3. Alert Dialog

Modal confirmation dialog that expects a response.

```tsx
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader,
  AlertDialogTitle, AlertDialogTrigger
} from "@/components/ui/alert-dialog"
```

| Prop (Content) | Values |
|----------------|--------|
| `size` | `"default"` / `"sm"` |

```tsx
<AlertDialog>
  <AlertDialogTrigger asChild><Button variant="destructive">Delete</Button></AlertDialogTrigger>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>Are you sure?</AlertDialogTitle>
      <AlertDialogDescription>This action cannot be undone.</AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel>Cancel</AlertDialogCancel>
      <AlertDialogAction>Delete</AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

---

### 4. Avatar

User image with fallback.

```tsx
import { Avatar, AvatarFallback, AvatarImage, AvatarBadge, AvatarGroup, AvatarGroupCount } from "@/components/ui/avatar"
```

| Prop (Avatar) | Values |
|---------------|--------|
| `size` | `"default"` / `"sm"` / `"lg"` |

```tsx
<Avatar>
  <AvatarImage src="/user.png" alt="User" />
  <AvatarFallback>JD</AvatarFallback>
</Avatar>
```

Grouping: `<AvatarGroup>` with `<AvatarGroupCount>` for "+3 more".

---

### 5. Badge

Status labels and tags.

```tsx
import { Badge } from "@/components/ui/badge"
```

| Prop | Values |
|------|--------|
| `variant` | `"default"` / `"secondary"` / `"destructive"` / `"outline"` / `"ghost"` / `"link"` |

```tsx
<Badge variant="secondary">Draft</Badge>
<Badge variant="destructive">Overdue</Badge>
```

Supports icons via `data-icon="inline-start"` / `data-icon="inline-end"`.

---

### 6. Breadcrumb

Navigation path hierarchy.

```tsx
import {
  Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList,
  BreadcrumbPage, BreadcrumbSeparator, BreadcrumbEllipsis
} from "@/components/ui/breadcrumb"
```

```tsx
<Breadcrumb>
  <BreadcrumbList>
    <BreadcrumbItem><BreadcrumbLink href="/">Home</BreadcrumbLink></BreadcrumbItem>
    <BreadcrumbSeparator />
    <BreadcrumbItem><BreadcrumbPage>Current Page</BreadcrumbPage></BreadcrumbItem>
  </BreadcrumbList>
</Breadcrumb>
```

---

### 7. Button

Primary interactive element.

```tsx
import { Button } from "@/components/ui/button"
```

| Prop | Values |
|------|--------|
| `variant` | `"default"` / `"outline"` / `"ghost"` / `"destructive"` / `"secondary"` / `"link"` |
| `size` | `"default"` / `"xs"` / `"sm"` / `"lg"` / `"icon"` / `"icon-xs"` / `"icon-sm"` / `"icon-lg"` |
| `asChild` | `boolean` — render as child element (e.g., Next.js Link) |

```tsx
<Button>Primary</Button>
<Button variant="outline">Secondary</Button>
<Button variant="destructive">Delete</Button>
<Button variant="ghost" size="icon"><Icons.settings /></Button>
```

Loading state: `<Button><Spinner data-icon="inline-start" /> Saving...</Button>`

---

### 8. Calendar

Date selection powered by React DayPicker.

```tsx
import { Calendar } from "@/components/ui/calendar"
```

| Prop | Values |
|------|--------|
| `mode` | `"single"` / `"range"` |
| `selected` | `Date` or `{ from: Date, to: Date }` |
| `onSelect` | callback |
| `captionLayout` | `"label"` / `"dropdown"` |

```tsx
<Calendar mode="single" selected={date} onSelect={setDate} className="rounded-lg border" />
```

---

### 9. Card

Content container with header/body/footer.

```tsx
import { Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
```

| Prop (Card) | Values |
|-------------|--------|
| `size` | `"default"` / `"sm"` |

```tsx
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description</CardDescription>
    <CardAction><Button size="sm">Edit</Button></CardAction>
  </CardHeader>
  <CardContent>Body content</CardContent>
  <CardFooter>Footer actions</CardFooter>
</Card>
```

---

### 10. Carousel

Scrollable content slider powered by Embla Carousel.

```tsx
import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious } from "@/components/ui/carousel"
```

| Prop | Values |
|------|--------|
| `orientation` | `"horizontal"` / `"vertical"` |
| `opts` | Embla config object (alignment, loop, etc.) |

```tsx
<Carousel>
  <CarouselContent>
    <CarouselItem>Slide 1</CarouselItem>
    <CarouselItem>Slide 2</CarouselItem>
  </CarouselContent>
  <CarouselPrevious />
  <CarouselNext />
</Carousel>
```

---

### 11. Chart

Data visualization powered by Recharts.

```tsx
import { ChartContainer, ChartTooltip, ChartTooltipContent, ChartLegend, ChartLegendContent } from "@/components/ui/chart"
import { BarChart, Bar, LineChart, Line, CartesianGrid, XAxis, YAxis } from "recharts"
```

Use `ChartConfig` object for labels, icons, and CSS variable colors. Wrap all charts in `<ChartContainer>`.

```tsx
<ChartContainer config={chartConfig} className="min-h-[200px]">
  <BarChart data={data}>
    <CartesianGrid vertical={false} />
    <XAxis dataKey="month" />
    <Bar dataKey="value" fill="var(--color-value)" radius={4} />
    <ChartTooltip content={<ChartTooltipContent />} />
  </BarChart>
</ChartContainer>
```

---

### 12. Checkbox

Toggle control for boolean values.

```tsx
import { Checkbox } from "@/components/ui/checkbox"
```

| Prop | Values |
|------|--------|
| `checked` | `boolean` (controlled) |
| `defaultChecked` | `boolean` (uncontrolled) |
| `onCheckedChange` | callback |
| `disabled` | `boolean` |

Use with `Field`, `FieldLabel` for accessible form fields.

---

### 13. Collapsible

Expand/collapse panel.

```tsx
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
```

```tsx
<Collapsible>
  <CollapsibleTrigger>Toggle Section</CollapsibleTrigger>
  <CollapsibleContent>Hidden content here</CollapsibleContent>
</Collapsible>
```

---

### 14. Combobox

Searchable dropdown — composed from Popover + Command (or use the Base UI Combobox).

```tsx
import { Combobox, ComboboxContent, ComboboxEmpty, ComboboxInput, ComboboxItem, ComboboxList } from "@/components/ui/combobox"
```

| Prop | Values |
|------|--------|
| `value` / `onValueChange` | controlled state |
| `multiple` | `boolean` for multi-select |
| `placeholder` | `string` |

For multi-select, use `ComboboxChips` + `ComboboxChipsInput`.

---

### 15. Command

Command palette / search menu (built on cmdk).

```tsx
import {
  Command, CommandDialog, CommandEmpty, CommandGroup, CommandInput,
  CommandItem, CommandList, CommandSeparator, CommandShortcut
} from "@/components/ui/command"
```

```tsx
<Command>
  <CommandInput placeholder="Search..." />
  <CommandList>
    <CommandEmpty>No results.</CommandEmpty>
    <CommandGroup heading="Actions">
      <CommandItem>Create New</CommandItem>
      <CommandItem>Search<CommandShortcut>Ctrl+K</CommandShortcut></CommandItem>
    </CommandGroup>
  </CommandList>
</Command>
```

Use `<CommandDialog>` for modal command palette (Ctrl+K pattern).

---

### 16. Context Menu

Right-click action menu.

```tsx
import {
  ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuTrigger,
  ContextMenuSeparator, ContextMenuCheckboxItem, ContextMenuRadioItem,
  ContextMenuSub, ContextMenuSubTrigger, ContextMenuSubContent, ContextMenuShortcut
} from "@/components/ui/context-menu"
```

`ContextMenuItem` supports `variant="destructive"`.

---

### 17. Data Table

Advanced table with sorting, filtering, pagination — built on TanStack Table + shadcn Table.

```tsx
import { ColumnDef, flexRender, getCoreRowModel, getPaginationRowModel, getSortedRowModel, getFilteredRowModel, useReactTable } from "@tanstack/react-table"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
```

**Column definition:**
```tsx
const columns: ColumnDef<T>[] = [
  { accessorKey: "name", header: "Name" },
  {
    accessorKey: "status",
    header: ({ column }) => <DataTableColumnHeader column={column} title="Status" />,
    cell: ({ row }) => <Badge>{row.getValue("status")}</Badge>,
  },
  { id: "actions", cell: ({ row }) => <DataTableRowActions row={row} /> },
]
```

**Table setup:**
```tsx
const table = useReactTable({
  data,
  columns,
  getCoreRowModel: getCoreRowModel(),
  getPaginationRowModel: getPaginationRowModel(),
  getSortedRowModel: getSortedRowModel(),
  getFilteredRowModel: getFilteredRowModel(),
  onSortingChange: setSorting,
  onColumnFiltersChange: setColumnFilters,
  onColumnVisibilityChange: setColumnVisibility,
  onRowSelectionChange: setRowSelection,
  state: { sorting, columnFilters, columnVisibility, rowSelection },
})
```

**Features:** sorting, column filters, global filter, column visibility toggle, row selection with checkboxes, pagination controls.

---

### 18. Date Picker

Composed from Popover + Calendar.

```tsx
import { format } from "date-fns"
import { CalendarIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
```

```tsx
<Popover>
  <PopoverTrigger asChild>
    <Button variant="outline">
      <CalendarIcon />
      {date ? format(date, "PPP") : "Pick a date"}
    </Button>
  </PopoverTrigger>
  <PopoverContent className="w-auto p-0">
    <Calendar mode="single" selected={date} onSelect={setDate} />
  </PopoverContent>
</Popover>
```

For range: use `mode="range"`. For DOB: use `captionLayout="dropdown"`.

---

### 19. Dialog

Modal overlay window.

```tsx
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
```

| Prop (Content) | Values |
|----------------|--------|
| `showCloseButton` | `boolean` (default true) |

```tsx
<Dialog>
  <DialogTrigger asChild><Button>Open</Button></DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Edit Item</DialogTitle>
      <DialogDescription>Make changes and save.</DialogDescription>
    </DialogHeader>
    {/* Form content */}
  </DialogContent>
</Dialog>
```

---

### 20. Drawer

Slide-out panel (mobile-friendly alternative to Dialog). Powered by Vaul.

```tsx
import { Drawer, DrawerClose, DrawerContent, DrawerDescription, DrawerFooter, DrawerHeader, DrawerTitle, DrawerTrigger } from "@/components/ui/drawer"
```

| Prop | Values |
|------|--------|
| `direction` | `"top"` / `"right"` / `"bottom"` / `"left"` |

```tsx
<Drawer>
  <DrawerTrigger>Open</DrawerTrigger>
  <DrawerContent>
    <DrawerHeader>
      <DrawerTitle>Title</DrawerTitle>
      <DrawerDescription>Description</DrawerDescription>
    </DrawerHeader>
    <DrawerFooter>
      <Button>Save</Button>
      <DrawerClose><Button variant="outline">Cancel</Button></DrawerClose>
    </DrawerFooter>
  </DrawerContent>
</Drawer>
```

---

### 21. Dropdown Menu

Action menu triggered by button click.

```tsx
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
  DropdownMenuGroup, DropdownMenuLabel, DropdownMenuSeparator,
  DropdownMenuCheckboxItem, DropdownMenuRadioGroup, DropdownMenuRadioItem,
  DropdownMenuShortcut, DropdownMenuSub, DropdownMenuSubTrigger, DropdownMenuSubContent
} from "@/components/ui/dropdown-menu"
```

`DropdownMenuItem` supports `variant="destructive"`.

```tsx
<DropdownMenu>
  <DropdownMenuTrigger asChild><Button variant="ghost" size="icon"><MoreHorizontal /></Button></DropdownMenuTrigger>
  <DropdownMenuContent align="end">
    <DropdownMenuLabel>Actions</DropdownMenuLabel>
    <DropdownMenuItem>Edit</DropdownMenuItem>
    <DropdownMenuSeparator />
    <DropdownMenuItem variant="destructive">Delete</DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

---

### 22. Form (React Hook Form + Zod)

Accessible form fields with validation.

```tsx
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
```

**Pattern:**
```tsx
const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) })

<Form {...form}>
  <form onSubmit={form.handleSubmit(onSubmit)}>
    <FormField control={form.control} name="fieldName" render={({ field }) => (
      <FormItem>
        <FormLabel>Label</FormLabel>
        <FormControl><Input {...field} /></FormControl>
        <FormDescription>Helper text</FormDescription>
        <FormMessage />
      </FormItem>
    )} />
    <Button type="submit">Submit</Button>
  </form>
</Form>
```

Alternative: use `Field`, `FieldLabel`, `FieldDescription` for simpler layouts without full form state.

---

### 23. Hover Card

Preview content on hover.

```tsx
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card"
```

| Prop | Values |
|------|--------|
| `openDelay` | `number` (ms) |
| `closeDelay` | `number` (ms) |

---

### 24. Input

Text input for forms.

```tsx
import { Input } from "@/components/ui/input"
```

Standard HTML input props: `type`, `placeholder`, `disabled`, `aria-invalid`, `required`, `value`, `onChange`.

Types: `text`, `email`, `password`, `file`, `number`, `search`, etc.

Use with `Field` + `FieldLabel` for accessible labeling. Use `InputGroup` for prefix/suffix addons.

---

### 25. Input OTP

One-time password / verification code input.

```tsx
import { InputOTP, InputOTPGroup, InputOTPSeparator, InputOTPSlot } from "@/components/ui/input-otp"
import { REGEXP_ONLY_DIGITS } from "input-otp"
```

```tsx
<InputOTP maxLength={6} pattern={REGEXP_ONLY_DIGITS}>
  <InputOTPGroup>
    <InputOTPSlot index={0} /><InputOTPSlot index={1} /><InputOTPSlot index={2} />
  </InputOTPGroup>
  <InputOTPSeparator />
  <InputOTPGroup>
    <InputOTPSlot index={3} /><InputOTPSlot index={4} /><InputOTPSlot index={5} />
  </InputOTPGroup>
</InputOTP>
```

---

### 26. Label

Accessible form label.

```tsx
import { Label } from "@/components/ui/label"
```

```tsx
<Label htmlFor="email">Email</Label>
```

---

### 27. Menubar

Desktop-style persistent menu bar.

```tsx
import {
  Menubar, MenubarMenu, MenubarTrigger, MenubarContent, MenubarItem,
  MenubarSeparator, MenubarShortcut, MenubarCheckboxItem,
  MenubarRadioGroup, MenubarRadioItem, MenubarSub, MenubarSubTrigger, MenubarSubContent
} from "@/components/ui/menubar"
```

```tsx
<Menubar>
  <MenubarMenu>
    <MenubarTrigger>File</MenubarTrigger>
    <MenubarContent>
      <MenubarItem>New<MenubarShortcut>Ctrl+N</MenubarShortcut></MenubarItem>
      <MenubarSeparator />
      <MenubarItem>Exit</MenubarItem>
    </MenubarContent>
  </MenubarMenu>
</Menubar>
```

---

### 28. Navigation Menu

Top-level site navigation with dropdown content areas.

```tsx
import {
  NavigationMenu, NavigationMenuContent, NavigationMenuItem, NavigationMenuLink,
  NavigationMenuList, NavigationMenuTrigger, navigationMenuTriggerStyle
} from "@/components/ui/navigation-menu"
```

```tsx
<NavigationMenu>
  <NavigationMenuList>
    <NavigationMenuItem>
      <NavigationMenuTrigger>Features</NavigationMenuTrigger>
      <NavigationMenuContent>
        <NavigationMenuLink href="/feature-a">Feature A</NavigationMenuLink>
      </NavigationMenuContent>
    </NavigationMenuItem>
    <NavigationMenuItem>
      <NavigationMenuLink asChild className={navigationMenuTriggerStyle()}>
        <Link href="/docs">Docs</Link>
      </NavigationMenuLink>
    </NavigationMenuItem>
  </NavigationMenuList>
</NavigationMenu>
```

---

### 29. Pagination

Page navigation controls.

```tsx
import {
  Pagination, PaginationContent, PaginationEllipsis, PaginationItem,
  PaginationLink, PaginationNext, PaginationPrevious
} from "@/components/ui/pagination"
```

```tsx
<Pagination>
  <PaginationContent>
    <PaginationItem><PaginationPrevious href="#" /></PaginationItem>
    <PaginationItem><PaginationLink href="#" isActive>1</PaginationLink></PaginationItem>
    <PaginationItem><PaginationLink href="#">2</PaginationLink></PaginationItem>
    <PaginationItem><PaginationEllipsis /></PaginationItem>
    <PaginationItem><PaginationNext href="#" /></PaginationItem>
  </PaginationContent>
</Pagination>
```

---

### 30. Popover

Floating content panel triggered by a button.

```tsx
import { Popover, PopoverContent, PopoverDescription, PopoverHeader, PopoverTitle, PopoverTrigger } from "@/components/ui/popover"
```

| Prop (Content) | Values |
|----------------|--------|
| `align` | `"start"` / `"center"` / `"end"` |

---

### 31. Progress

Progress bar indicator.

```tsx
import { Progress } from "@/components/ui/progress"
```

```tsx
<Progress value={66} />
```

---

### 32. Radio Group

Single-select option group.

```tsx
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
```

```tsx
<RadioGroup defaultValue="option-1">
  <div className="flex items-center gap-3">
    <RadioGroupItem value="option-1" id="opt-1" />
    <Label htmlFor="opt-1">Option 1</Label>
  </div>
  <div className="flex items-center gap-3">
    <RadioGroupItem value="option-2" id="opt-2" />
    <Label htmlFor="opt-2">Option 2</Label>
  </div>
</RadioGroup>
```

---

### 33. Resizable

Resizable panel layouts.

```tsx
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable"
```

| Prop (PanelGroup) | Values |
|--------------------|--------|
| `orientation` | `"horizontal"` / `"vertical"` |

| Prop (Handle) | Values |
|---------------|--------|
| `withHandle` | `boolean` — show visible drag handle |

---

### 34. Scroll Area

Custom scrollbar styling.

```tsx
import { ScrollArea } from "@/components/ui/scroll-area"
```

```tsx
<ScrollArea className="h-72 w-full rounded-md border">
  {/* Long content */}
</ScrollArea>
```

Use `ScrollBar orientation="horizontal"` for horizontal scrolling.

---

### 35. Select

Dropdown selection.

```tsx
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectSeparator, SelectTrigger, SelectValue } from "@/components/ui/select"
```

```tsx
<Select>
  <SelectTrigger className="w-[200px]">
    <SelectValue placeholder="Choose..." />
  </SelectTrigger>
  <SelectContent>
    <SelectGroup>
      <SelectLabel>Category</SelectLabel>
      <SelectItem value="a">Option A</SelectItem>
      <SelectItem value="b">Option B</SelectItem>
    </SelectGroup>
  </SelectContent>
</Select>
```

---

### 36. Separator

Visual divider.

```tsx
import { Separator } from "@/components/ui/separator"
```

| Prop | Values |
|------|--------|
| `orientation` | `"horizontal"` (default) / `"vertical"` |

---

### 37. Sheet

Slide-in panel from screen edge (extends Dialog).

```tsx
import { Sheet, SheetClose, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
```

| Prop (Content) | Values |
|----------------|--------|
| `side` | `"top"` / `"right"` (default) / `"bottom"` / `"left"` |
| `showCloseButton` | `boolean` |

```tsx
<Sheet>
  <SheetTrigger asChild><Button>Open Panel</Button></SheetTrigger>
  <SheetContent side="right">
    <SheetHeader>
      <SheetTitle>Details</SheetTitle>
      <SheetDescription>View and edit details.</SheetDescription>
    </SheetHeader>
    {/* Content */}
    <SheetFooter>
      <SheetClose asChild><Button variant="outline">Close</Button></SheetClose>
      <Button>Save</Button>
    </SheetFooter>
  </SheetContent>
</Sheet>
```

---

### 38. Sidebar

Application sidebar navigation.

```tsx
import {
  SidebarProvider, Sidebar, SidebarContent, SidebarFooter, SidebarHeader,
  SidebarGroup, SidebarGroupLabel, SidebarGroupContent, SidebarGroupAction,
  SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarMenuAction, SidebarMenuBadge,
  SidebarMenuSub, SidebarMenuSubItem, SidebarMenuSubButton, SidebarMenuSkeleton,
  SidebarTrigger, SidebarRail, useSidebar
} from "@/components/ui/sidebar"
```

| Prop (Sidebar) | Values |
|----------------|--------|
| `variant` | `"sidebar"` / `"floating"` / `"inset"` |
| `collapsible` | `"offcanvas"` / `"icon"` / `"none"` |

**useSidebar hook:** `state`, `open`, `setOpen`, `toggleSidebar`, `isMobile`, `openMobile`, `setOpenMobile`.

CSS variables: `--sidebar-width`, `--sidebar-width-mobile`, `--sidebar-background`, `--sidebar-foreground`, `--sidebar-primary`, `--sidebar-accent`, `--sidebar-border`.

---

### 39. Skeleton

Loading placeholder.

```tsx
import { Skeleton } from "@/components/ui/skeleton"
```

```tsx
{/* Avatar skeleton */}
<Skeleton className="h-12 w-12 rounded-full" />

{/* Text lines skeleton */}
<div className="space-y-2">
  <Skeleton className="h-4 w-3/4" />
  <Skeleton className="h-4 w-full" />
</div>

{/* Card skeleton */}
<Skeleton className="h-[200px] w-full rounded-xl" />
```

---

### 40. Slider

Range value input.

```tsx
import { Slider } from "@/components/ui/slider"
```

| Prop | Values |
|------|--------|
| `defaultValue` | `number[]` |
| `max` | `number` |
| `step` | `number` |
| `orientation` | `"horizontal"` / `"vertical"` |
| `disabled` | `boolean` |

Multiple thumbs: pass array with multiple values.

---

### 41. Sonner (Toast)

Toast notifications. Replaces the deprecated Toast component.

```tsx
import { toast } from "sonner"
import { Toaster } from "@/components/ui/sonner"
```

**Setup:** Add `<Toaster />` to root layout.

**Trigger toasts:**
```tsx
toast("Default message")
toast.success("Saved successfully")
toast.error("Something went wrong")
toast.warning("Check your input")
toast.info("New update available")
toast.promise(asyncFn, { loading: "Saving...", success: "Done!", error: "Failed" })
```

| Prop (Toaster) | Values |
|----------------|--------|
| `position` | `"top-left"` / `"top-center"` / `"top-right"` / `"bottom-left"` / `"bottom-center"` / `"bottom-right"` |

---

### 42. Switch

Toggle between on/off states.

```tsx
import { Switch } from "@/components/ui/switch"
```

Props: `checked`, `onCheckedChange`, `disabled`, `size`.

Use with `Field` + `FieldLabel` for accessible form layout.

---

### 43. Table

Basic styled table (non-interactive). For interactive tables, see Data Table (#17).

```tsx
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
```

```tsx
<Table>
  <TableCaption>Recent invoices</TableCaption>
  <TableHeader>
    <TableRow>
      <TableHead>Invoice</TableHead>
      <TableHead>Status</TableHead>
      <TableHead className="text-right">Amount</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    <TableRow>
      <TableCell>INV-001</TableCell>
      <TableCell><Badge>Paid</Badge></TableCell>
      <TableCell className="text-right">$250.00</TableCell>
    </TableRow>
  </TableBody>
</Table>
```

---

### 44. Tabs

Tabbed content panels.

```tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
```

| Prop (Tabs) | Values |
|-------------|--------|
| `defaultValue` | `string` |
| `orientation` | `"horizontal"` / `"vertical"` |

| Prop (TabsList) | Values |
|-----------------|--------|
| `variant` | `"default"` / `"line"` |

```tsx
<Tabs defaultValue="general">
  <TabsList>
    <TabsTrigger value="general">General</TabsTrigger>
    <TabsTrigger value="security">Security</TabsTrigger>
  </TabsList>
  <TabsContent value="general">General settings</TabsContent>
  <TabsContent value="security">Security settings</TabsContent>
</Tabs>
```

---

### 45. Textarea

Multi-line text input.

```tsx
import { Textarea } from "@/components/ui/textarea"
```

Standard HTML textarea props: `placeholder`, `disabled`, `aria-invalid`, `rows`, `value`, `onChange`.

---

### 46. Toggle

Two-state button (on/off).

```tsx
import { Toggle } from "@/components/ui/toggle"
```

| Prop | Values |
|------|--------|
| `variant` | `"default"` / `"outline"` |
| `size` | `"default"` / `"sm"` / `"lg"` |
| `disabled` | `boolean` |

---

### 47. Toggle Group

Group of exclusive or multi-select toggles.

```tsx
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
```

| Prop | Values |
|------|--------|
| `type` | `"single"` / `"multiple"` |
| `variant` | `"default"` / `"outline"` |
| `orientation` | `"horizontal"` / `"vertical"` |

---

### 48. Tooltip

Hover/focus information popup.

```tsx
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
```

**Setup:** Wrap app root with `<TooltipProvider>`.

| Prop (Content) | Values |
|----------------|--------|
| `side` | `"top"` / `"right"` / `"bottom"` / `"left"` |

```tsx
<Tooltip>
  <TooltipTrigger asChild><Button size="icon"><HelpCircle /></Button></TooltipTrigger>
  <TooltipContent><p>Help text here</p></TooltipContent>
</Tooltip>
```

---

## Common Composition Patterns

### Page with Data Table
```
Breadcrumb → H2 heading + description → toolbar (Input search + Select filters + Button actions) → DataTable → Pagination
```

### Form Page / Dialog
```
Dialog/Sheet → Form → FormField items (Input, Select, Textarea, Checkbox, RadioGroup, DatePicker, Switch) → Button submit/cancel
```

### Settings Page
```
Tabs → TabsContent panels → Card sections → Form fields inside each card
```

### Dashboard Page
```
Cards (stat summaries) → Charts (bar/line/area) → Data Table (recent items)
```

### List with Actions
```
Card per item → CardHeader (title + DropdownMenu actions) → CardContent (details) → CardFooter (Badge status)
```

### Empty State
```
Card → centered illustration/icon → H3 title → Muted description → Button CTA
```

### Loading State
```
Skeleton placeholders matching the final layout shape (avatar circles, text lines, card rectangles)
```

### Error State
```
Alert variant="destructive" → AlertTitle + AlertDescription + AlertAction (retry button)
```

### Confirmation Flow
```
AlertDialog → destructive action confirmation with Cancel + Action buttons
```

### Command Palette
```
CommandDialog (Ctrl+K) → CommandInput → CommandList → CommandGroup sections → CommandItem actions
```

### Navigation Layout
```
SidebarProvider → Sidebar (nav groups + menu items) → main content area with SidebarTrigger in header
```
