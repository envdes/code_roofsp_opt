module UrbSprinklingIrrigationMod

#include "shr_assert.h"
    
      !-----------------------------------------------------------------------
      ! !DESCRIPTION:
      ! Implements urban sprinkling and irrigation
      !
      ! !PUBLIC TYPES:
      use shr_kind_mod      , only : r8 => shr_kind_r8
      use shr_log_mod       , only : errMsg => shr_log_errMsg
      !use decompMod         , only : bounds_type

      use atm2lndType       , only : atm2lnd_type
      !use Wateramt2lndType  , only : wateramt2lnd_type
      use SoilstateType     , only : soilstate_type
      use TemperatureType   , only : temperature_type
      use WaterstateType    , only : waterstate_type
      use WaterfluxType     , only : waterflux_type
      use EnergyFluxType    , only : energyflux_type
      use LandunitType      , only : lun                
      use ColumnType        , only : col     
      use QSatMod           , only : QSat
      !
      implicit none
      !
      ! !PUBLIC MEMBER FUNCTIONS:
      public :: UrbSprinklingIrrigation

      !-----------------------------------------------------------------------
    
    contains
    
      !-----------------------------------------------------------------------
      subroutine UrbSprinklingIrrigation(  tod, &
            num_nolakec   , filter_nolakec,  &
            temperature_inst, atm2lnd_inst, & 
            soilstate_inst, waterstate_inst, waterflux_inst, energyflux_inst)
        !
        ! !DESCRIPTION:
        ! Implements urban sprinkling and irrigation
        ! Hyperparameters:
        ! alpha1: road sprinkling intensity coefficient
        ! alpha2: road irrigation intensity coefficient
        ! T_threshold: temperature threshold for irrigation
        ! urban_sprinkling_time: time of day for urban sprinkling
        ! urban_irrigation_time: time of day for urban irrigation
        
        ! !USES:
        use shr_orb_mod
        use clm_time_manager    , only : get_step_size
        use column_varcon       , only : icol_road_perv, icol_road_imperv, icol_roof
        use landunit_varcon     , only : istsoil, istcrop, isturb_md
        use abortutils          , only : endrun

        implicit none
    
        ! !ARGUMENTS:
        integer                , intent(in)            :: tod                  ! time of day (s)
        integer                , intent(in)            :: num_nolakec          ! number of columns in no-lake columns
        integer                , intent(in)            :: filter_nolakec(:)    ! column filter for no-lake columns
        type(atm2lnd_type)     , intent(inout)         :: atm2lnd_inst
        !type(wateramt2lnd_type), intent(inout)         :: wateramt2lnd_inst
        type(waterstate_type)  , intent(in)            :: waterstate_inst
        type(waterflux_type)   , intent(inout)         :: waterflux_inst
        type(temperature_type) , intent(in)            :: temperature_inst
        type(soilstate_type)   , intent(in)            :: soilstate_inst
        type(energyflux_type)  , intent(in)            :: energyflux_inst

        !
        ! !LOCAL VARIABLES: urban sprinkling and irrigation
        integer  :: c                                                                         ! index for columns [idx]
        integer  :: l                                                                         ! index for landunits [idx]
        integer  :: g                                                                         ! index for gridcells [idx]
        integer  :: fc                                                                        ! index for filter columns [idx]
        integer  :: hour                                                                      ! hour of the day
        real(r8) :: dtime                                                                     ! land model time step (s)
        real(r8) :: road_spinkling                                                            ! road sprinkling intensity (mm)                                                         ! road irrigation intensity (mm)
        real(r8) :: alpha1                                                                    ! road sprinkling intensity coefficient
        real(r8) :: alpha2                                                                    ! road irrigation intensity coefficient
        !real(r8) :: epsilon                                                                   ! small number to avoid division by zero
        real(r8) :: pondmx_urban                                                              ! maximum ponding depth in urban areas (m)
        real(r8)  :: action_mode                                                               ! action mode
        real(r8) :: tg_threshold                                                              ! temperature threshold for spr (K)

        !-----------------------------------------------------------------------
    
       associate(&
              ctype               =>    col%itype                                         , & ! Input:  [integer  (:)    ]  column type         
              h2osoi_liq          =>    waterstate_inst%h2osoi_liq_col                    , & ! Input:  [real(r8)  (:,:) ]  col liquid water (kg/m2) (new) (-nlevsno+1:nlevgrnd) 
              h2osoi_vol          =>    waterstate_inst%h2osoi_vol_col                    , & ! Input:  [real(r8)  (:,:) ]  col volumetric soil water (0<=h2osoi_vol<=watsat) [m3/m3]  (nlevgrnd)
              qg                  =>    waterstate_inst%qg_col                            , & ! Input:  [real(r8)  (:)   ]  ground specific humidity (kg/kg) at the surface column
              qaf                 =>    waterstate_inst%qaf_lun                           , & ! Input:  [real(r8)  (:)   ]  lun urban canopy air specific humidity (kg/kg)
              water_tank          =>    waterstate_inst%water_tank_col                    , & ! Output: [real(r8) (:)   ]  water tank (mm)        
              qflx_water_tank_out =>    waterflux_inst%qflx_water_tank_out_col           , & ! Output: [real(r8) (:)   ]  water tank outflow (mm/s)
              taf                 =>    temperature_inst%taf_lun                          , & ! Input:  [real(r8)  (:)   ]  canyon air temperature (K) 
              t_grnd              =>    temperature_inst%t_grnd_col                       , & ! Input:  [real(r8) (:)    ]  ground surface temperature (K)  
              !sac_action          =>    temperature_inst%sac_action                       , & ! Output: [real(r8)  (:)   ]  action for SAC model
              !sac_action_water_budget => temperature_inst%sac_action_water_budget         , & ! Output: [real(r8)  (:)   ]  water budget for SAC model

              watsat              =>    soilstate_inst%watsat_col                         , & ! Input:  [real(r8) (:,:) ] volumetric soil water at saturation (porosity)  
              eff_porosity        =>    soilstate_inst%eff_porosity_col                   , & ! Input:  [real(r8) (:,:) ] effective porosity = porosity - vol_ice  
              eflx_urban_ac       =>    energyflux_inst%eflx_urban_ac_lun                 , & ! Output:  [real(r8) (:)]  urban air conditioning flux (W/m**2)
              eflx_urban_heat     =>    energyflux_inst%eflx_urban_heat_lun               , &  ! Output:  [real(r8) (:)]  urban heating flux (W/m**2)

              forc_pbot           =>    atm2lnd_inst%forc_pbot_downscaled_col             , & ! Input:  [real(r8)  (:)  ]  atmospheric pressure at the bottom of the column (Pa)
              forc_solar_g        =>    atm2lnd_inst%forc_solar_grc                          , & ! Input:  [real(r8) (:)]  gridcell direct incoming solar radiation
              forc_t              =>    atm2lnd_inst%forc_t_not_downscaled_grc                , & ! Input:  [real(r8)  (:)  ]  atmospheric temperature at the surface column (K)
              !rainf               =>    wateramt2lnd_inst%forc_rain_downscaled_col        , & ! Output:  [real(r8)  (:)  ]  rainfall rate (mm/s) at the surface column
              rainf               =>    atm2lnd_inst%forc_rain_downscaled_col             & ! Output:  [real(r8)  (:)  ]  rainfall rate (mm/s) at the surface column
              )

        !-----------------------------------------------------------------------
         ! Get step size

         dtime = get_step_size()

         hour = INT(tod / 3600)

         OPEN(UNIT=30, FILE="/p/clmuapp/action_mode.txt", STATUS="OLD", ACTION="READWRITE")
         REWIND(30)
         read(30,*) action_mode
         close(30)

         OPEN(UNIT=30, FILE="/p/clmuapp/tg_threshold.txt", STATUS="OLD", ACTION="READWRITE")
         REWIND(30)
         read(30,*) tg_threshold
         close(30)

        if (INT(action_mode) == -1) then
            call random_seed()
            call random_number(alpha1) ! 生成随机数，并存储到 alpha1 中
            alpha1 = alpha1 * 0.2_r8
        !else if (action_mode == 0) then
        !    alpha1 = action(1)
        else 
            alpha1 = action_mode / 100.0_r8
        end if

        !write(*,*) 'action: ', action
        !write(*,*) 'alpha1: ', alpha1
         pondmx_urban = 1.0_r8
         road_spinkling = alpha1 * pondmx_urban/dtime

         do fc = 1,num_nolakec
            c = filter_nolakec(fc)
            l = col%landunit(c)

            qflx_water_tank_out(c) = 0.0_r8 ! fixed bug: reset water tank outflow to zero at each time step
            if (lun%itype(l) == isturb_md) then
                !if (ctype(c) == icol_road_imperv) then
                if (ctype(c) == icol_roof .and. t_grnd(c) >= tg_threshold .and. water_tank(c) > 0.0_r8) then

                    if (road_spinkling*dtime >= water_tank(c)) then
                        road_spinkling = water_tank(c)/dtime
                        water_tank(c) = 0.0_r8
                    else
                        water_tank(c) = water_tank(c) - road_spinkling*dtime
                    end if

                    rainf(c) = rainf(c) + road_spinkling
                    write(*,*) 'road sprinkling: ', road_spinkling
                    qflx_water_tank_out(c) = road_spinkling
                end if

            end if

         end do
        end associate 
      end subroutine UrbSprinklingIrrigation
    
end module UrbSprinklingIrrigationMod
    