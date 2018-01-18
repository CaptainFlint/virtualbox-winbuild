/* $Id$ */
/** @file
 * DevHDA.h - Header file for VBox Intel HD Audio Controller.
 */

/*
 * Copyright (C) 2017 Oracle Corporation
 *
 * This file is part of VirtualBox Open Source Edition (OSE), as
 * available from http://www.virtualbox.org. This file is free software;
 * you can redistribute it and/or modify it under the terms of the GNU
 * General Public License (GPL) as published by the Free Software
 * Foundation, in version 2 as it comes in the "COPYING" file of the
 * VirtualBox OSE distribution. VirtualBox OSE is distributed in the
 * hope that it will be useful, but WITHOUT ANY WARRANTY of any kind.
 */

#ifndef DEV_HDA_H
#define DEV_HDA_H

#include <iprt/circbuf.h>

/**
 * Internal state of a Buffer Descriptor List Entry (BDLE),
 * needed to keep track of the data needed for the actual device
 * emulation.
 */
typedef struct HDABDLESTATE
{
    /** Own index within the BDL (Buffer Descriptor List). */
    uint32_t     u32BDLIndex;
    /** Number of bytes below the stream's FIFO watermark (SDFIFOW).
     *  Used to check if we need fill up the FIFO again. */
    uint32_t     cbBelowFIFOW;
    /** Current offset in BDLE buffer (in samples). */
    uint32_t     u32BufOff;
    uint32_t     Padding;
} HDABDLESTATE, *PHDABDLESTATE;

/**
 * BDL description structure.
 * Do not touch this, as this must match to the HDA specs.
 */
typedef struct HDABDLEDESC
{
    /** Starting address of the actual buffer. Must be 128-bit aligned. */
    uint64_t     u64BufAdr;
    /** Size of the actual buffer (in bytes). */
    uint32_t     u32BufSize;
    /** Bit 0: Interrupt on completion; the controller will generate
     *  an interrupt when the last byte of the buffer has been
     *  fetched by the DMA engine.
     *
     *  Rest is reserved for further use and must be 0. */
    uint32_t     fFlags;
} HDABDLEDESC, *PHDABDLEDESC;
AssertCompileSize(HDABDLEDESC, 16); /* Always 16 byte. Also must be aligned on 128-byte boundary. */

/**
 * Buffer Descriptor List Entry (BDLE) (3.6.3).
 *
 * Contains only register values which do *not* change until a
 * stream reset occurs.
 */
typedef struct HDABDLE
{
    /** The actual BDL description. */
    HDABDLEDESC    Desc;
    /** Internal state of this BDLE.
     *  Not part of the actual BDLE registers. */
    HDABDLESTATE   State;
} HDABDLE, *PHDABDLE;

struct HDASTREAMPERIOD;

/**
 * Internal state of a HDA stream.
 */
typedef struct HDASTREAMSTATE
{
    /** Current BDLE to use. Wraps around to 0 if
     *  maximum (cBDLE) is reached. Zero-based. */
    uint16_t                uCurBDLE;
    /** Flag indicating whether this stream is in an
     *  active (operative) state or not. */
    volatile bool           fRunning;
    /** Flag indicating whether this stream currently is
     *  in reset mode and therefore not acccessible by the guest. */
    volatile bool           fInReset;
    /** Unused, padding. */
    bool                    fPadding0;
    /** Current BDLE (Buffer Descriptor List Entry). */
    HDABDLE                 BDLE;
    /** The stream's internal FIFO buffer. */
    R3PTRTYPE(PRTCIRCBUF)   pCircBuf;
    /** Timestamp of the last DMA data transfer. */
    uint64_t                tsTransferLast;
    /** Timestamp of the next DMA data transfer.
     *  Next for determining the next scheduling window.
     *  Can be 0 if no next transfer is scheduled. */
    uint64_t                tsTransferNext;
    /** Total transfer size (in bytes) of a transfer period. */
    uint32_t                cbTransferSize;
    /** Transfer chunk size (in bytes) of a transfer period. */
    uint32_t                cbTransferChunk;
    /** How many bytes already have been processed in within
     *  the current transfer period. */
    uint32_t                cbTransferProcessed;
    /** How many interrupts are pending due to
     *  BDLE interrupt-on-completion (IOC) bits set. */
    uint8_t                 cTransferPendingInterrupts;
    uint8_t                 Padding1[4];
    /** How many audio data frames are left to be processed
     *  for the position adjustment handling.
     *
     *  0 if position adjustment handling is done or inactive. */
    uint16_t                cPosAdjustFramesLeft;
    uint8_t                 Padding2[2];
    /** (Virtual) clock ticks per byte. */
    uint64_t                cTicksPerByte;
    /** (Virtual) clock ticks per transfer. */
    uint64_t                cTransferTicks;
    /** The stream's period. Need for timing.  */
    HDASTREAMPERIOD         Period;
    /** The stream's current configuration.
     *  Should match SDFMT. */
    PDMAUDIOSTREAMCFG       strmCfg;
# ifdef HDA_USE_DMA_ACCESS_HANDLER
    /** List of DMA handlers. */
    RTLISTANCHORR3          lstDMAHandlers;
#endif
} HDASTREAMSTATE, *PHDASTREAMSTATE;

#if defined (DEBUG) || defined(HDA_USE_DMA_ACCESS_HANDLER)
typedef struct HDASTREAMDBGINFO
{
    /** Critical section to serialize access if needed. */
    RTCRITSECT              CritSect;
    uint32_t                Padding1[2];
    /** Number of total read accesses. */
    uint64_t                cReadsTotal;
    /** Number of total DMA bytes read. */
    uint64_t                cbReadTotal;
    /** Timestamp (in ns) of last read access. */
    uint64_t                tsLastReadNs;
    /** Number of total write accesses. */
    uint64_t                cWritesTotal;
    /** Number of total DMA bytes written. */
    uint64_t                cbWrittenTotal;
    /** Number of total write accesses since last iteration (Hz). */
    uint64_t                cWritesHz;
    /** Number of total DMA bytes written since last iteration (Hz). */
    uint64_t                cbWrittenHz;
    /** Timestamp (in ns) of beginning a new write slot. */
    uint64_t                tsWriteSlotBegin;
    /** Number of current silence samples in a (consecutive) row. */
    uint64_t                csSilence;
    /** Number of silent samples in a row to consider an audio block as audio gap (silence). */
    uint64_t                cSilenceThreshold;
    /** How many bytes to skip in an audio stream before detecting silence.
     *  (useful for intros and silence at the beginning of a song). */
    uint64_t                cbSilenceReadMin;
} HDASTREAMDBGINFO ,*PHDASTREAMDBGINFO;
#endif /* defined (DEBUG) || defined(HDA_USE_DMA_ACCESS_HANDLER) */

/**
 * Structure for keeping a HDA stream state.
 *
 * Contains only register values which do *not* change until a
 * stream reset occurs.
 */
typedef struct HDASTREAM
{
    /** Stream descriptor number (SDn). */
    uint8_t          u8SD;
    uint8_t          Padding0[7];
    /** DMA base address (SDnBDPU - SDnBDPL). */
    uint64_t         u64BDLBase;
    /** Cyclic Buffer Length (SDnCBL).
     *  Represents the size of the complete cyclic buffer (in bytes). */
    uint32_t         u32CBL;
    /** FIFO Size (FIFOS).
     *  Maximum number of bytes that may have been DMA'd into
     *  memory but not yet transmitted on the link.
     *
     *  Must be a power of two. */
    uint16_t         u16FIFOS;
    /** Last Valid Index (SDnLVI). Zero-based. */
    uint16_t         u16LVI;
    uint16_t         Padding1[3];
    /** Internal state of this stream. */
    HDASTREAMSTATE   State;
#ifdef DEBUG
    /** Debug information. */
    HDASTREAMDBGINFO Dbg;
#endif
} HDASTREAM, *PHDASTREAM;

#endif /* !DEV_HDA_H */

