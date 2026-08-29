import type { SVGProps } from "react";

export default function LogoIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      {...props}
    >
      <rect width="32" height="32" rx="6" fill="currentColor" />
      <path
        d="M8 22V10h2v5l4-5h2.5l-3.5 4.5L17 22h-2.5l-3-5L10 17.5V22H8z"
        fill="#fff"
      />
    </svg>
  );
}
