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
  const [animationKey, setAnimationKey] = useState(0);
  const tickerRef = useRef<HTMLDivElement>(null);
  
  // Combine joke lines into full text for ticker
  useEffect(() => {
    if (!joke) {
      setDisplayText('');
      return;
    }
    
    // Combine line1 and line2 with appropriate separator
    let fullText = joke.line1;
    if (joke.line2) {
      fullText += '   ···   ' + joke.line2;
    }
    
    // Reset animation by changing key
    setDisplayText(fullText);
    setAnimationKey(prev => prev + 1);
  }, [joke]);
  
  // Don't render if no joke to display
  if (!joke || !displayText) {
    return null;
  }
  
  // Calculate animation duration: longer text = longer duration
  // Base speed: roughly 50 characters per 10 seconds
  const duration = Math.max(12, displayText.length * 0.2);
  
  return (
    <div className="w-full overflow-hidden bg-gradient-to-r from-amber-900/30 via-amber-800/20 to-amber-900/30 border-b border-amber-500/30">
      <div className="relative flex items-center h-8">
        {/* Left icon - fixed position */}
        <div className="flex-shrink-0 flex items-center gap-2 px-4 z-10 bg-gradient-to-r from-amber-900/90 via-amber-900/80 to-transparent pr-8">
          <Smile className="w-4 h-4 text-amber-400" />
          <span className="text-xs font-medium text-amber-400 hidden sm:inline">JOKE</span>
        </div>
        
        {/* Scrolling ticker container - takes remaining space */}
        <div 
          ref={tickerRef}
          className="flex-1 overflow-hidden relative"
        >
          <div 
            key={animationKey}
            className="ticker-scroll whitespace-nowrap text-sm text-amber-100/90 font-medium"
            style={{
              animationDuration: `${duration}s`,
            }}
          >
            <span className="inline-block">{displayText}</span>
          </div>
        </div>
        
        {/* Right sparkle icon - fixed position */}
        <div className="flex-shrink-0 pl-8 px-4 z-10 bg-gradient-to-l from-amber-900/90 via-amber-900/80 to-transparent">
          <Sparkles className="w-4 h-4 text-amber-400/70" />
        </div>
      </div>
    </div>
  );
}

// Export the JokeData type for use in other components
export type { JokeData as JokeTickerData };

