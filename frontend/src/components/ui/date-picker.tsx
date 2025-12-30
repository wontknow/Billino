"use client";

import React, { useState } from "react";
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, X } from "lucide-react";
import { Button } from "./button";
import { Popover, PopoverContent, PopoverTrigger } from "./popover";

interface DatePickerProps {
  value?: string;
  onValueChange?: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

interface DateRangePickerProps {
  valueFrom?: string;
  valueTo?: string;
  onValueFromChange?: (value: string) => void;
  onValueToChange?: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

/**
 * Single Date Picker with calendar
 */
export const DatePicker: React.FC<DatePickerProps> = ({
  value,
  onValueChange,
  placeholder = "Datum wählen",
  disabled,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [calendarMonth, setCalendarMonth] = useState<Date>(
    value ? new Date(value + "T00:00:00") : new Date()
  );

  const handleDateSelect = (day: number) => {
    // Construct ISO date string directly to avoid timezone issues
    const year = calendarMonth.getFullYear();
    const month = String(calendarMonth.getMonth() + 1).padStart(2, "0");
    const dayStr = String(day).padStart(2, "0");
    const isoDate = `${year}-${month}-${dayStr}`;
    onValueChange?.(isoDate);
    setIsOpen(false);
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onValueChange?.("");
  };

  const displayValue = value
    ? new Intl.DateTimeFormat("de-DE", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }).format(new Date(value + "T00:00:00"))
    : placeholder;

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className="w-full justify-start text-left font-normal gap-2"
          disabled={disabled}
        >
          <CalendarIcon className="h-4 w-4 opacity-50" />
          <span className={value ? "" : "text-muted-foreground"}>{displayValue}</span>
          {value && (
            <X className="ml-auto h-4 w-4 opacity-50 hover:opacity-100" onClick={handleClear} />
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          selectedDate={value}
          onSelectDate={handleDateSelect}
          currentMonth={calendarMonth}
          onMonthChange={setCalendarMonth}
        />
      </PopoverContent>
    </Popover>
  );
};

/**
 * Date Range Picker with calendar
 */
export const DateRangePicker: React.FC<DateRangePickerProps> = ({
  valueFrom,
  valueTo,
  onValueFromChange,
  onValueToChange,
  placeholder = "Von - Bis",
  disabled,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [calendarMonth, setCalendarMonth] = useState<Date>(
    valueFrom ? new Date(valueFrom + "T00:00:00") : new Date()
  );
  const [selectingFrom, setSelectingFrom] = useState(true);

  const handleDateSelect = (day: number) => {
    // Construct ISO date string directly to avoid timezone issues
    const year = calendarMonth.getFullYear();
    const month = String(calendarMonth.getMonth() + 1).padStart(2, "0");
    const dayStr = String(day).padStart(2, "0");
    const isoDate = `${year}-${month}-${dayStr}`;

    if (selectingFrom) {
      onValueFromChange?.(isoDate);
      setSelectingFrom(false);
    } else {
      if (valueFrom && isoDate < valueFrom) {
        onValueFromChange?.(isoDate);
        onValueToChange?.(valueFrom);
      } else {
        onValueToChange?.(isoDate);
      }
      setIsOpen(false);
    }
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onValueFromChange?.("");
    onValueToChange?.("");
    setSelectingFrom(true);
  };

  const formatDate = (dateStr: string) =>
    new Intl.DateTimeFormat("de-DE", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(dateStr + "T00:00:00"));

  const displayValue =
    valueFrom && valueTo
      ? `${formatDate(valueFrom)} – ${formatDate(valueTo)}`
      : valueFrom
        ? formatDate(valueFrom)
        : placeholder;

  const hasValue = valueFrom || valueTo;

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className="w-full justify-start text-left font-normal gap-2"
          disabled={disabled}
        >
          <CalendarIcon className="h-4 w-4 opacity-50 flex-shrink-0" />
          <span className={`flex-1 ${hasValue ? "" : "text-muted-foreground"}`}>
            {displayValue}
          </span>
          {hasValue && (
            <X
              className="h-4 w-4 opacity-50 hover:opacity-100 flex-shrink-0"
              onClick={handleClear}
            />
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[280px] p-0" align="start">
        <div className="p-3 border-b bg-muted/50">
          <div className="text-sm font-medium mb-1 min-h-5">
            {selectingFrom ? "Startdatum wählen" : "Enddatum wählen"}
          </div>
          <div className="text-xs text-muted-foreground min-h-4">
            {selectingFrom
              ? "Wählen Sie ein Datum oder einen Bereich"
              : "Gleiches Datum = einzelner Tag"}
          </div>
        </div>
        <Calendar
          selectedDate={selectingFrom ? valueFrom : valueTo}
          rangeStart={valueFrom}
          rangeEnd={valueTo}
          onSelectDate={handleDateSelect}
          currentMonth={calendarMonth}
          onMonthChange={setCalendarMonth}
        />
      </PopoverContent>
    </Popover>
  );
};

interface CalendarProps {
  selectedDate?: string;
  rangeStart?: string;
  rangeEnd?: string;
  onSelectDate: (day: number) => void;
  currentMonth: Date;
  onMonthChange: (date: Date) => void;
}

function Calendar({
  selectedDate,
  rangeStart,
  rangeEnd,
  onSelectDate,
  currentMonth,
  onMonthChange,
}: CalendarProps) {
  const daysInMonth = new Date(
    currentMonth.getFullYear(),
    currentMonth.getMonth() + 1,
    0
  ).getDate();

  const firstDayOfMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1).getDay();

  const days = [];
  for (let i = 0; i < firstDayOfMonth; i++) {
    days.push(null);
  }
  for (let i = 1; i <= daysInMonth; i++) {
    days.push(i);
  }

  const handlePrevMonth = () => {
    const prev = new Date(currentMonth);
    prev.setMonth(prev.getMonth() - 1);
    onMonthChange(prev);
  };

  const handleNextMonth = () => {
    const next = new Date(currentMonth);
    next.setMonth(next.getMonth() + 1);
    onMonthChange(next);
  };

  const isDateInRange = (day: number): boolean => {
    if (!rangeStart || !rangeEnd) return false;
    const dateStr = `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    return dateStr >= rangeStart && dateStr <= rangeEnd;
  };

  const isSelectedDate = (day: number): boolean => {
    if (!selectedDate) return false;
    const dateStr = `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    return dateStr === selectedDate;
  };

  const isRangeStart = (day: number): boolean => {
    if (!rangeStart) return false;
    const dateStr = `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    return dateStr === rangeStart;
  };

  const isRangeEnd = (day: number): boolean => {
    if (!rangeEnd) return false;
    const dateStr = `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    return dateStr === rangeEnd;
  };

  return (
    <div className="p-3 space-y-3">
      <div className="flex items-center justify-between px-1">
        <button
          onClick={handlePrevMonth}
          className="p-1.5 hover:bg-muted rounded-md transition-colors"
          aria-label="Vorheriger Monat"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <div className="text-sm font-semibold">
          {currentMonth.toLocaleDateString("de-DE", {
            month: "long",
            year: "numeric",
          })}
        </div>
        <button
          onClick={handleNextMonth}
          className="p-1.5 hover:bg-muted rounded-md transition-colors"
          aria-label="Nächster Monat"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      <div className="grid grid-cols-7 gap-1">
        {["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"].map((day) => (
          <div
            key={day}
            className="text-center text-xs font-semibold text-muted-foreground h-8 flex items-center justify-center"
          >
            {day}
          </div>
        ))}

        {days.map((day, idx) => {
          const isToday =
            day &&
            new Date().toDateString() ===
              new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day).toDateString();

          return (
            <button
              key={idx}
              onClick={() => day && onSelectDate(day)}
              className={`
                h-8 text-sm rounded-md flex items-center justify-center transition-all font-medium
                ${!day ? "cursor-default invisible" : "cursor-pointer hover:bg-accent hover:text-accent-foreground"}
                ${day && isSelectedDate(day) ? "bg-primary text-primary-foreground font-bold shadow-sm" : ""}
                ${day && (isRangeStart(day) || isRangeEnd(day)) ? "bg-primary text-primary-foreground font-bold shadow-sm" : ""}
                ${day && isDateInRange(day) && !isRangeStart(day) && !isRangeEnd(day) ? "bg-primary/20 text-primary-foreground/90" : ""}
                ${isToday && !isSelectedDate(day) && !isRangeStart(day) && !isRangeEnd(day) ? "border-2 border-primary" : ""}
              `}
              disabled={!day}
              aria-label={
                day
                  ? `${day}. ${currentMonth.toLocaleDateString("de-DE", { month: "long" })}`
                  : undefined
              }
            >
              {day}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default DatePicker;
