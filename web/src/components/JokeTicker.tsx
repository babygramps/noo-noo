'use client';

import { useState, useEffect, useRef } from 'react';
import { Smile, Sparkles } from 'lucide-react';

export interface JokeData {
  line1: string;
  line2: string;
}

interface JokeTickerProps {
  joke: JokeData | null;
  isConnected: boolean;
}

export function JokeTicker({ joke, isConnected }: JokeTickerProps) {
  const [displayText, setDisplayText] = useState<string>('');
  const [isAnimating, setIsAnimating] = useState(false);
  const tickerRef = useRef<HTMLDivElement>(null);
  
  // Combine joke lines into full text for ticker
  useEffect(() => {
    if (!joke) {
      setDisplayText('');
      setIsAnimating(false);
      return;
    }
    
    // Combine line1 and line2 with appropriate separator
    let fullText = joke.line1;
    if (joke.line2) {
      fullText += '   ···   ' + joke.line2;
    }
    
    // Trigger animation
    setIsAnimating(false);
    setTimeout(() => {
      setDisplayText(fullText);
      setIsAnimating(true);
    }, 50);
  }, [joke]);
  
  // Don't render if no joke to display
  if (!joke || !displayText) {
    return null;
  }
  
  return (
    <div className="w-full overflow-hidden bg-gradient-to-r from-amber-900/30 via-amber-800/20 to-amber-900/30 border-b border-amber-500/30">
      <div className="relative flex items-center h-8 px-4">
        {/* Left icon */}
        <div className="flex-shrink-0 flex items-center gap-2 pr-4 z-10 bg-gradient-to-r from-amber-900/80 to-transparent">
          <Smile className="w-4 h-4 text-amber-400" />
          <span className="text-xs font-medium text-amber-400 hidden sm:inline">JOKE</span>
        </div>
        
        {/* Scrolling ticker container */}
        <div 
          ref={tickerRef}
          className="flex-1 overflow-hidden relative"
        >
          <div 
            className={`
              whitespace-nowrap text-sm text-amber-100/90 font-medium
              ${isAnimating ? 'animate-ticker' : ''}
            `}
            style={{
              // Calculate animation duration based on text length
              animationDuration: `${Math.max(15, displayText.length * 0.15)}s`,
            }}
          >
            {/* Double the text for seamless looping */}
            <span className="inline-block px-8">{displayText}</span>
            <span className="inline-block px-8">{displayText}</span>
          </div>
        </div>
        
        {/* Right sparkle icon */}
        <div className="flex-shrink-0 pl-4 z-10 bg-gradient-to-l from-amber-900/80 to-transparent">
          <Sparkles className="w-4 h-4 text-amber-400/70" />
        </div>
      </div>
    </div>
  );
}

// Export the JokeData type for use in other components
export type { JokeData as JokeTickerData };

